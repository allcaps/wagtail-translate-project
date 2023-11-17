import json
from collections import defaultdict

from django.apps import AppConfig
import codecs

from django.db import transaction
from wagtail_localize.machine_translators.dummy import DummyTranslator



def translate(value):
    return codecs.encode(value, 'rot13')

def translate_page(source_page, target_page):
    source_locale = source_page.locale.language_code
    target_locale = target_page.locale.language_code
    target_page.title = translate(source_page.title)
    revision = target_page.save_revision()
    return revision


class BabelfishConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "babelfish"

    def ready(self):
        from wagtail.actions.copy_for_translation import copy_for_translation_done
        from django.dispatch import receiver
        from .components import TranslationComponentManager
        from .operations import translate_object
        from .models import StringTranslation
        from .segments import StringSegmentValue
        from .models import Translation

        @receiver(copy_for_translation_done)
        def actual_translation(sender, page, translated_page, **kwargs):
            """Signal handler to do the actual translation of the page"""

            # wagtail_localize.views.submit_translations.SubmitTranslationView.dispatch
            components = TranslationComponentManager.from_request(
                None, source_object_instance=page
            )

            # wagtail_localize.views.submit_translations.SubmitTranslationView.post
            # wagtail_localize.views.submit_translations.SubmitTranslationView.form_valid
            translate_object(
                translated_page,
                [translated_page.locale],
                components,
                None,
            )

            # wagtail_localize.views.edit_translation.stop_translation
            translation = Translation.objects.get(
                source__object_id=page.translation_key,
                target_locale_id=translated_page.locale_id,
                enabled=True,
            )

            translator = DummyTranslator({})

            # Get segments
            segments = defaultdict(list)
            for string_segment in translation.source.stringsegment_set.all().select_related(
                    "context", "string"
            ):
                segment = StringSegmentValue(
                    string_segment.context.path,
                    string_segment.string.as_value()
                ).with_order(string_segment.order)
                if string_segment.attrs:
                    segment.attrs = json.loads(string_segment.attrs)

                # Don't translate if there already is a translation
                # if StringTranslation.objects.filter(
                #         translation_of_id=string_segment.string_id,
                #         locale=translated_page.locale,
                #         context_id=string_segment.context_id,
                # ).exists():
                #     continue

                segments[segment.string].append(
                    (string_segment.string_id, string_segment.context_id)
                )

            if segments:
                translations = translator.translate(
                    page.locale,
                    translated_page.locale,
                    segments.keys()
                )

                with transaction.atomic():
                    for string, contexts in segments.items():
                        for string_id, context_id in contexts:
                            print(string_id, context_id)
                            StringTranslation.objects.get_or_create(
                                translation_of_id=string_id,
                                locale=translation.target_locale,
                                context_id=context_id,
                                defaults={
                                    "data": translations[string].data,
                                    "translation_type": StringTranslation.TRANSLATION_TYPE_MACHINE,
                                    "tool_name": translator.display_name,
                                    "last_translated_by": None,
                                    "has_error": False,
                                    "field_error": "",
                                },
                            )

            translation.enabled = False
            translation.save(update_fields=["enabled"])
