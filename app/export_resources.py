from django.db.models import ForeignKey
from import_export import resources, widgets

from app.models import Room


# Related models whose __str__ is not a good export label: model -> attribute to export instead.
FK_LABEL_ATTRIBUTES = {
    Room: "number",  # Room.__str__ also includes the current free/occupied status
}


class ReadableExportResource(resources.ModelResource):
    """Export with human-readable values: Russian column headers (verbose_name),
    related objects by name instead of id, and choice labels instead of codes."""

    @classmethod
    def field_from_django_field(cls, field_name, django_field, readonly):
        field = super().field_from_django_field(field_name, django_field, readonly)
        verbose_name = django_field.verbose_name
        if isinstance(django_field, ForeignKey) and django_field._verbose_name is None:
            # FK without an explicit verbose_name: use the related model's name
            verbose_name = django_field.related_model._meta.verbose_name
        field.column_name = str(verbose_name)

        if isinstance(django_field, ForeignKey):
            label_attr = FK_LABEL_ATTRIBUTES.get(django_field.related_model)
            field.attribute = f"{field_name}__{label_attr}" if label_attr else field_name
            field.widget = widgets.Widget()  # renders str(value)
        elif django_field.choices:
            field.attribute = f"get_{field_name}_display"
            field.widget = widgets.Widget()

        return field


def readable_resource(model):
    return resources.modelresource_factory(model, resource_class=ReadableExportResource)
