import html
import core.block_tokenizer as tokenizer
from core.leaf_token import tokenize_inner
import lib.html_renderer as renderer

__all__ = ['Heading', 'Quote', 'Paragraph', 'BlockCode',
           'List', 'ListItem', 'Separator']

class BlockToken(object):
    def __init__(self, content, tagname, tokenize_func):
        self.children = tokenize_func(content)
        self.tagname = tagname

    def render(self):
        inner = ''.join([ token.render() for token in self.children ])
        return renderer.tagify(self.tagname, inner)

class Heading(BlockToken):
    # pre: line = "### heading 3\n"
    def __init__(self, line):
        hashes, content = line.strip().split(' ', 1)
        tagname = "h{}".format(len(hashes))
        super().__init__(content, tagname, tokenize_inner)

class Quote(BlockToken):
    # pre: lines[i] = "> some text\n"
    def __init__(self, lines):
        content = [ line[2:] for line in lines ]
        super().__init__(content, 'blockquote', tokenize)

class Paragraph(BlockToken):
    # pre: lines = ["some\n", "continuous\n", "lines\n"]
    def __init__(self, lines):
        content = ' '.join([ line.strip() for line in lines ])
        super().__init__(content, 'p', tokenize_inner)

class BlockCode(BlockToken):
    # pre: lines = ["```sh\n", "rm -rf /", ..., "```"]
    def __init__(self, lines):
        self.content = ''.join(lines[1:-1]) # implicit newlines
        self.language = lines[0].strip()[3:]

    def render(self):
        attrs = { 'class': self.language }
        content = html.escape(self.content)
        inner = renderer.tagify_attrs('code', attrs, content)
        return renderer.tagify('pre', inner)

class List(BlockToken):
    # pre: items = [
    # "- item 1\n",
    # "- item 2\n",
    # "    - nested item\n",
    # "- item 3\n"
    # ]
    def __init__(self):
        self.children = []
        self.tagname = 'ul'

    def add(self, item):
        self.children.append(item)

class ListItem(BlockToken):
    # pre: line = "- some *italics* text\n"
    def __init__(self, line):
        super().__init__(line.strip()[2:], 'li', tokenize_inner)

class Separator(BlockToken):
    def __init__(self, line):
        pass

    def render(self):
        return '<hr>'

def tokenize(lines):
    import core.block_token as block_token

    tokens = []
    index = 0

    def shift_token(token_type, tokenize_func):
        end_index = tokenize_func(index, lines)
        tokens.append(token_type(lines[index:end_index]))
        return end_index

    def build_list(lines, level=0):
        l = block_token.List()
        index = 0
        while index < len(lines):
            curr_line = lines[index][level*4:]
            if curr_line.startswith('- '):
                l.add(block_token.ListItem(lines[index]))
            elif curr_line.startswith(' '*4):
                curr_level = level + 1
                end_index = tokenizer.read_list(index, lines, curr_level)
                l.add(build_list(lines[index:end_index], curr_level))
                index = end_index - 1
            index += 1
        return l

    def shift_line_token(token_type=None):
        if token_type:
            tokens.append(token_type(lines[index]))
        return index + 1

    while index < len(lines):
        if lines[index].startswith('#'):        # heading
            index = shift_line_token(Heading)
        elif lines[index].startswith('> '):     # quote
            index = shift_token(Quote, tokenizer.read_quote)
        elif lines[index].startswith('```'):    # block code
            index = shift_token(BlockCode, tokenizer.read_block_code)
        elif lines[index] == '---\n':           # separator
            index = shift_line_token(Separator)
        elif lines[index].startswith('- '):     # list
            index = shift_token(build_list, tokenizer.read_list)
        elif lines[index] == '\n':              # skip empty line
            index = shift_line_token()
        else:                                   # paragraph
            index = shift_token(Paragraph, tokenizer.read_paragraph)
    return tokens