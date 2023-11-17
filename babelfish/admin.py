from django.contrib import admin

from .models import (
    TranslatableObject,
    TranslationSource,
    Translation,
    TranslationLog,
    String, StringTranslation,
)




admin.site.register(TranslatableObject)
admin.site.register(TranslationSource)
admin.site.register(Translation)
admin.site.register(StringTranslation)
admin.site.register(TranslationLog)


class StringAdmin(admin.ModelAdmin):
    list_display = [
        "__str__",
        "locale",
        "data",
    ]

admin.site.register(String, StringAdmin)