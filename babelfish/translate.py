import codecs

from bs4 import BeautifulSoup, NavigableString
from wagtail import blocks
from wagtail.fields import RichTextField, StreamField

from wagtail.rich_text import RichText

from .fields import get_translatable_fields


def lstrip_keep(text: str) -> (str, str):
    """
    Like lstrip, but also returns the whitespace that was stripped off
    """
    text_length = len(text)
    new_text = text.lstrip()
    prefix = text[0 : (text_length - len(new_text))]
    return new_text, prefix


def rstrip_keep(text: str) -> (str, str):
    """
    Like rstrip, but also returns the whitespace that was stripped off
    """
    text_length = len(text)
    new_text = text.rstrip()
    if text_length != len(new_text):
        suffix = text[-(text_length - len(new_text)) :]
    else:
        suffix = ""
    return new_text, suffix


class Translator:
    source_language_code: str
    target_language_code: str

    def __init__(self, source_language_code, target_language_code):
        self.source_language_code = source_language_code
        self.target_language_code = target_language_code

    def translate(self, source_string: str) -> str:
        """
        Translate, a function that does the actual translation.
        This will probably be replaced by a call to a translation service.

        ROT13 is used to demonstrate this POC.
        """
        # Rot13 does not need this information,
        # but a real translation service would.
        self.source_language_code  # noqa
        self.target_language_code  # noqa

        return codecs.encode(source_string, 'rot13')

    def translate_html_string(self, string: str) -> str:
        """
        Translate HTML string,

        Translates the string and preserves the left and right whitespace.

        HTML collapses whitespace, however left and right whitespace needs
        to be preserved, as it may be significant. For example, the whitespace
        in the following strings are significant:

            <p><strong>Hello</strong> World</p>
            <p><strong>Hello </strong>World</p>
        """
        string, left_whitespace = lstrip_keep(string)
        string, right_whitespace = rstrip_keep(string)
        translation = self.translate(string)
        return f"{left_whitespace}{translation}{right_whitespace}"

    def translate_html(self, html: str) -> str:
        """
        Translate HTML,

        - Recursively walks the HTML tree, and translates the strings
        - Preserves whitespace
        - Translates attributes, alt and title

        Unfortunately, this is not a perfect solution, as it translates
        string segments one by one, and does not take into account the overall
        context of the string. For example, the following string:

            <p><strong>Hello</strong> World</p>

        Will be translated in two parts, "Hello" and "World",
        and ideally would be translated as "Hello World".

        I expect the loss off context be a hindrance to the translation service.
        Not sure how to solve this problem. Passing the whole HTML has the risk
        of translating tags and attributes which is undesirable.
        """
        soup = BeautifulSoup(html, "html.parser")

        def walk(soup):
            for child in soup.children:
                if isinstance(child, NavigableString):
                    # Translate navigable strings
                    child.string.replace_with(
                        self.translate_html_string(child.string)
                    )
                else:
                    # Recursively walk the tree
                    walk(child)

        walk(soup)

        # loop through all tags and translate title and alt attributes.
        for tag in soup.find_all():
            if tag.has_attr('title'):
                tag['title'] = self.translate(tag['title'])
            if tag.has_attr('alt'):
                tag['alt'] = self.translate(tag['alt'])

        return str(soup)


    # def handle_block(block_type, block_value, raw_value=None):
    #     Need to check if the app is installed before importing EmbedBlock
    #     See: https://github.com/wagtail/wagtail-localize/issues/309
    #     if apps.is_installed("wagtail.embeds"):
    #         from wagtail.embeds.blocks import EmbedBlock
    #
    #         if isinstance(block_type, EmbedBlock):
    #             if self.include_overridables:
    #                 return [OverridableSegmentValue("", block_value.url)]
    #             else:
    #                 return []

    def translate_struct_block(self, item):
        """"""
        # for idx, obj in enumerate(item.bound_blocks):
        #     print(idx, obj, item.bound_blocks[obj].value)
        return item

    def translate_stream_block(self, item):
        # for index, block in enumerate(item):
        #     raw_data = stream_block.raw_data[index]
        #     handle_block(
        #         block.block, block.value, raw_value=raw_data
        #     )
        return item  # TODO, implement

    def translate_list_block(self, item):
        return item  # TODO, implement

    def translate_block(self, item) -> None:
        """
        Translate (a streamfield) block,

        Receives a block, discovers its type, and translates its value.
        Sets the value on the block, returns None.

        Skips if the field is not translatable.
        """
        if isinstance(item.block, (blocks.CharBlock, blocks.TextBlock)):
            item.value = self.translate(item.value)
        elif isinstance(item.block, blocks.RichTextBlock):
            item.value = RichText(self.translate_html(str(item.value)))
        elif isinstance(item.block, blocks.RawHTMLBlock):
            item.value = self.translate_html(item.value)
        elif isinstance(item.block, blocks.StructBlock):
            item.value = self.translate_struct_block(item)
        elif isinstance(item.block, blocks.BlockQuoteBlock):
            ...  # TODO, implement
        elif isinstance(item.block, blocks.ChooserBlock):
            ...  # TODO, implement
        elif isinstance(item.block, blocks.PageChooserBlock):
            ...  # TODO, implement
        else:
            # All other blocks are skipped. Like:
            # URLBlock, BooleanBlock, DateBlock, TimeBlock, DateTimeBlock,
            # ChoiceBlock, MultipleChoiceBlock, EmailBlock, IntegerBlock,
            # FloatBlock, DecimalBlock, RegexBlock, StaticBlock,
            ...

    def translate_blocks(self, items):
        """
        Translate blocks,

        Iterate over the StreamField/Streamblock/Listblock/StuctBlock.

        Recurse if Streamblock/Listblock/StuctBlock,
        or translate the block if it is a leaf.

        Recurse is indirect, as it calls a specific method for each block type.
        The specific method will prep the data and call this method to recurse.
        """
        for item in items:
            if isinstance(item.block, blocks.StructBlock):
                self.translate_struct_block(item)
            elif isinstance(item.block, blocks.StreamBlock):
                self.translate_stream_block(item)
            elif isinstance(item.block, blocks.ListBlock):
                self.translate_list_block(item)
            else:
                self.translate_block(item)

        return items

    def translate_obj(self, source_obj, target_obj):
        """
        Translate object,

        Translate an object. Returns the target object.

        Note, does not save the target object. This is left to the caller.
        """
        for field in get_translatable_fields(target_obj.__class__):
            src = getattr(source_obj, field.name)
            if isinstance(field, RichTextField):
                translation = self.translate_html(src)
            elif isinstance(field, StreamField):
                translation = self.translate_blocks(src)
            else:
                translation = self.translate(src)
            setattr(target_obj, field.name, translation)

        return target_obj
