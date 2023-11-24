from wagtail.actions.copy_for_translation import copy_for_translation_done
from django.dispatch import receiver
from wagtail.models import Page, TranslatableMixin
from .translate import Translator


@receiver(copy_for_translation_done)
def actual_translation(sender, source, target, **kwargs):
    """
    Actual translation,

    Wagtail will trigger the copy_for_translation_done signal,
    And this signal handler will translate the contents.

    The object must be a subclass of TranslatableMixin.

    Having a signal handler allows tailoring the behavior. For example,
    - Subclass Translator and override methods to tailor the behavior.
    - Pages can be draft (to be reviewed)
        or published (to be seen by the public).
    - Trigger a workflow
    - Post-process the data
    """
    if not issubclass(target.__class__, TranslatableMixin):
        raise Exception(
            "Object must be a subclass of TranslatableMixin. "
            f"Got {type(target)}."
        )

    # Get the source and target language codes
    source_language_code = source.locale.language_code
    target_language_code = target.locale.language_code

    # Initialize the translator, and translate.
    translator = Translator(source_language_code, target_language_code)
    translated_obj = translator.translate_obj(source, target)

    # Differentiate between page and regular Django model.
    # - Page instances have `save_revision` and `publish` methods.
    # - Regular Django model (aka Wagtail Snippet) need to be saved.
    if isinstance(translated_obj, Page):
        # Calling `publish` is optional,
        # and will publish the translated page.
        # Without, the page will be in draft mode.
        translated_obj.save_revision().publish()
    else:
        translated_obj.save()
