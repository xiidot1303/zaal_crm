from dataclasses import dataclass
from typing import Optional
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ExtBot,
    TypeHandler,
    PicklePersistence,
    ConversationHandler
)
from telegram import (
    ReplyKeyboardMarkup
)
from bot.resources.strings import Strings
import json
from telegram.ext import BasePersistence
import redis.asyncio as redis
from typing import Dict, Any


@dataclass
class NewsletterUpdate:
    user_id: int
    text: str
    photo: Optional[object | str] = None
    video: Optional[object | str] = None
    document: Optional[object] = None
    location: Optional[dict] = None
    reply_markup: Optional[ReplyKeyboardMarkup] = None
    pin_message: bool = False


class CustomContext(CallbackContext[ExtBot, dict, dict, dict]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.words = Strings(self._user_id)

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "CustomContext":
        if isinstance(update, NewsletterUpdate):
            return cls(application=application, user_id=update.user_id)
        return super().from_update(update, application)



class RedisPersistence(BasePersistence):
    def __init__(self, redis_url="redis://localhost:6379/12", prefix="ptb:", ttl=None):
        super().__init__()
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.prefix = prefix
        self.ttl = ttl

    # ---------- helpers ----------
    def _key(self, *parts):
        return self.prefix + ":".join(parts)

    async def _set(self, key: str, value: Any):
        data = json.dumps(value)
        if self.ttl:
            await self.redis.set(key, data, ex=self.ttl)
        else:
            await self.redis.set(key, data)

    async def _get(self, key: str, default):
        data = await self.redis.get(key)
        return json.loads(data) if data else default

    async def _delete(self, key: str):
        await self.redis.delete(key)

    def _str_to_tuple(self, s):
        return tuple(map(int, s.strip("()").split(", ")))

    # ---------- USER DATA ----------
    async def get_user_data(self) -> Dict[int, Dict]:
        result = {}
        async for key in self.redis.scan_iter(self._key("user_data", "*")):
            user_id = int(key.split(":")[-1])
            result[user_id] = await self._get(key, {})
        return result

    async def update_user_data(self, user_id: int, data: Dict):
        await self._set(self._key("user_data", str(user_id)), data)

    async def drop_user_data(self, user_id: int):
        await self._delete(self._key("user_data", str(user_id)))

    async def refresh_user_data(self, user_id: int, user_data: Dict):
        # called before handler runs → usually no-op for Redis
        return user_data

    # ---------- CHAT DATA ----------
    async def get_chat_data(self) -> Dict[int, Dict]:
        result = {}
        async for key in self.redis.scan_iter(self._key("chat_data", "*")):
            chat_id = int(key.split(":")[-1])
            result[chat_id] = await self._get(key, {})
        return result

    async def update_chat_data(self, chat_id: int, data: Dict):
        await self._set(self._key("chat_data", str(chat_id)), data)

    async def drop_chat_data(self, chat_id: int):
        await self._delete(self._key("chat_data", str(chat_id)))

    async def refresh_chat_data(self, chat_id: int, chat_data: Dict):
        return chat_data

    # ---------- BOT DATA ----------
    async def get_bot_data(self) -> Dict:
        return await self._get(self._key("bot_data"), {})

    async def update_bot_data(self, data: Dict):
        await self._set(self._key("bot_data"), data)

    async def refresh_bot_data(self, bot_data: Dict):
        return bot_data

    # ---------- CALLBACK DATA ----------
    async def get_callback_data(self) -> Dict:
        return await self._get(self._key("callback_data"), {})

    async def update_callback_data(self, data: Dict):
        await self._set(self._key("callback_data"), data)

    # ---------- CONVERSATIONS ----------
    async def get_conversations(self, name: str) -> dict:
        data = await self._get(self._key("conv", name), {})
        # convert stringified tuple keys back to tuples
        result = {}
        for k, v in data.items():
            result[self._str_to_tuple(k)] = v
        return result

    async def update_conversations(self, name: str, data: dict):
        # convert tuple keys to strings for JSON
        store_data = {str(k): v for k, v in data.items()}
        await self._set(self._key("conv", name), store_data)

    async def update_conversation(self, name: str, key: tuple, new_state: int | None):
        conv = await self.get_conversations(name)
        if new_state is None or new_state == ConversationHandler.END:
            # remove conversation key
            conv.pop(key, None)
        else:
            conv[key] = new_state

        await self.update_conversations(name, conv)
        
    # ---------- FLUSH ----------
    async def flush(self):
        pass