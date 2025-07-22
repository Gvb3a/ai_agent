
'''
<<<========================== WARNING ==========================>>>
All code in this file was taken from https://github.com/theurs/tb1.
It's unreadable, I don't understand it, but it works perfectly.
<<<========================== WARNING ==========================>>>
'''


import html
from pylatexenc.latex2text import LatexNodes2Text
import re
from prettytable import PrettyTable
from textwrap import wrap
import random
import string



def replace_code_lang(t: str) -> str:
    """
    Replaces the code language in the given string with appropriate HTML tags.
    Adds "language-plaintext" class if no language is specified but <code> tags are present.
    Does not add language class for single-line code snippets.
    Parameters:
        t (str): The input string containing code snippets.
    Returns:
        str: The modified string with code snippets wrapped in HTML tags.
    """
    result = ''
    code_content = ''
    state = 0
    lines = t.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        if state == 0 and line.startswith('<code>'):
            # Начало блока кода
            if '</code>' in line:
                # Однострочный код
                result += line + '\n'  # Оставляем без изменений
            else:
                lang = line[6:].strip().lower()
                if lang == 'c++':
                    lang = 'cpp'
                elif not lang:
                    lang = 'plaintext'
                result += f'<pre><code class="language-{lang}">'
                state = 1
                code_content = ''  # Не добавляем первую строку, так как она содержит только тег
        elif state == 1:
            if '</code>' in line:
                # Конец блока кода
                code_content += line[:line.index('</code>')]
                result += code_content + '</code></pre>\n'
                state = 0
            else:
                code_content += line + '\n'
        else:
            result += line + '\n'
        i += 1
    result = re.sub(r"\n{2,}</code>", "\n</code>", result)
    return result


def replace_latex(text: str) -> str:
    def is_valid_latex(text: str) -> bool:
        """
        Проверяет, является ли текст валидным LaTeX выражением
        """
        # Базовая проверка на наличие LaTeX команд или математических символов
        latex_indicators = [
            '\\', '_', '^', '{', '}', '=',  # базовые LaTeX команды
            '\\frac', '\\sqrt', '\\sum', '\\int',  # математические операторы
            '\\alpha', '\\beta', '\\gamma',  # греческие буквы
            '\\mathbf', '\\mathrm', '\\text'  # форм
        ]
        # Проверяем наличие хотя бы одного индикатора LaTeX
        return any(indicator in text for indicator in latex_indicators)


    # Обработка LaTeX выражений
    # 1. Сначала ищем выражения в $$ ... $$
    matches = re.findall(r'\$\$(.*?)\$\$', text, flags=re.DOTALL)
    for match in matches:
        if is_valid_latex(match):  # добавим проверку на валидность LaTeX
            try:
                new_match = LatexNodes2Text().latex_to_text(match.replace('\\\\', '\\'))
                new_match = html.escape(new_match)
                text = text.replace(f'$${match}$$', new_match)
            except:
                # Если возникла ошибка при конвертации, оставляем как есть
                continue

    # 2. Затем ищем выражения в $ ... $
    # matches = re.findall(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', text, flags=re.DOTALL)
    matches = re.findall(r'(?<!\$)\$(?!$)(.*?)(?<!\$)\$(?!$)', text, flags=re.DOTALL)
    for match in matches:
        if is_valid_latex(match):
            try:
                new_match = LatexNodes2Text().latex_to_text(match.replace('\\\\', '\\'))
                new_match = html.escape(new_match)
                text = text.replace(f'${match}$', new_match)
            except:
                continue

    # 3. Обработка \[ ... \] и \( ... \)
    matches = re.findall(r'\\\[(.*?)\\\]|\\\((.*?)\\\)', text, flags=re.DOTALL)
    for match_tuple in matches:
        match = match_tuple[0] if match_tuple[0] else match_tuple[1]
        if is_valid_latex(match):
            try:
                new_match = LatexNodes2Text().latex_to_text(match.replace('\\\\', '\\'))
                new_match = html.escape(new_match)
                if match_tuple[0]:
                    text = text.replace(f'\\[{match}\\]', new_match)
                else:
                    text = text.replace(f'\\({match}\\)', new_match)
            except:
                continue

    def latex_to_text(latex_formula):
        # Здесь должна быть реализация преобразования LaTeX в текст
        # В данном примере просто возвращаем формулу без изменений
        r = LatexNodes2Text().latex_to_text(latex_formula).strip()
        rr = html.escape(r)
        return rr

    def replace_function_lt1(match):
        latex_code = match.group(2) if match.group(2) is not None else match.group(3) if match.group(3) is not None else match.group(4)
        return latex_to_text(latex_code)

    pattern = r"\\begin\{(.*?)\}(.*?)\\end\{\1\}|\\\[(.*?)\\\]|\\begin(.*?)\\end"
    text = re.sub(pattern, replace_function_lt1, text, flags=re.DOTALL)

    return text


def replace_tables(text: str, max_width: int = 80, max_cell_width: int = 20, ) -> str:
    """
    Заменяет markdown таблицы на их prettytable представление.
    Улучшена обработка различных форматов таблиц, включая ограничение ширины и обрезание длинных заголовков.
    
    :param text: Исходный текст с markdown таблицами
    :param max_width: Максимальная ширина таблицы в символах
    :param max_cell_width: Максимальная ширина ячейки в символах
    :return: Текст с замененными таблицами
    """
    original_text = text
    try:
        text += '\n'

        def is_valid_separator(line: str) -> bool:
            if not line or not line.strip('| '):
                return False
            parts = line.strip().strip('|').split('|')
            return all(part.strip().replace('-', '').replace(':', '') == '' for part in parts)

        def is_valid_table_row(line: str) -> bool:
            return line.strip().startswith('|') and line.strip().endswith('|')

        def strip_tags(text: str) -> str:
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&#x27;', "'")
            text = text.replace('<b>', '   ')
            text = text.replace('<i>', '   ')
            text = text.replace('</b>', '    ')
            text = text.replace('</i>', '    ')
            text = text.replace('<br>', '    ')
            text = text.replace('<code>',  '      ')
            text = text.replace('</code>', '       ')
            return text

        def truncate_text(text: str, max_width: int) -> str:
            text = strip_tags(text)
            if len(text) <= max_width:
                return text
            return text[:max_width-3] + '...'

        def wrap_long_text(text: str, max_width: int) -> str:
            text = strip_tags(text)
            if len(text) <= max_width:
                return text
            return '\n'.join(wrap(text, max_width))

        def process_table(table_text: str) -> str:
            lines = table_text.strip().split('\n')
            x = PrettyTable()
            x.header = True
            x.hrules = 1

            # Находим заголовок и разделитель
            header_index = next((i for i, line in enumerate(lines) if is_valid_table_row(line)), None)
            if header_index is None:
                return table_text

            separator_index = next((i for i in range(header_index + 1, len(lines)) if is_valid_separator(lines[i])), None)
            if separator_index is None:
                return table_text

            # Обработка заголовка
            header = [truncate_text(cell.strip(), max_cell_width) for cell in lines[header_index].strip('|').split('|') if cell.strip()]

            def make_strings_unique(strings):
                """
                Проверяет список строк на наличие дубликатов и делает их уникальными.

                Args:
                    strings: Список строк.

                Returns:
                    Список строк без дубликатов.
                """
                seen = set()
                result = []
                for s in strings:
                    original_s = s
                    count = 1
                    while s in seen:
                        s = original_s + f"_{count}"
                        count += 1
                    seen.add(s)
                    result.append(s)
                return result

            x.field_names = make_strings_unique(header)

            # Настройка выравнивания на основе разделителя
            alignments = []
            for cell in lines[separator_index].strip('|').split('|'):
                cell = cell.strip()
                if cell.startswith(':') and cell.endswith(':'):
                    alignments.append('c')
                elif cell.endswith(':'):
                    alignments.append('r')
                else:
                    alignments.append('l')
            
            for i, align in enumerate(alignments):
                x.align[x.field_names[i]] = align

            # Обработка данных
            seen_rows = set()
            for line in lines[separator_index + 1:]:
                if is_valid_table_row(line) and not is_valid_separator(line):
                    row = [wrap_long_text(cell.strip(), max_cell_width) for cell in line.strip('|').split('|') if cell.strip()]
                    row += [''] * (len(header) - len(row))
                    row = tuple(row[:len(header)])
                    if row not in seen_rows:
                        seen_rows.add(row)
                        x.add_row(row)

            # Установка максимальной ширины таблицы
            x.max_width = max_width

            # return f'\n\n<pre><code>{x.get_string()}\n</code></pre>'
            return f'\n\n<code>{x.get_string()}\n</code>'

        # Находим все таблицы в тексте
        table_pattern = re.compile(r'(\n|^)\s*\|.*\|.*\n\s*\|[-:\s|]+\|\s*\n(\s*\|.*\|.*\n)*', re.MULTILINE)

        # Заменяем каждую найденную таблицу
        text = table_pattern.sub(lambda m: process_table(m.group(0)), text)


        # экранируем запрещенные символы кроме хтмл тегов
        TAG_MAP = {
            "<b>": "40bd001563085fc35165329ea1ff5c5ecbdbbeef",
            "</b>": "c591326762260728871710537179fabf75973234",
            "<strong>": "ef0b585e265b5287aa6d26a6860e0cd846623679",
            "</strong>": "e882cf5c82a930662f17c188c70ade885c55c607",
            "<i>": "497603a6c32112169ae39a79072c07e863ae3f7a",
            "</i>": "0784921025d4c05de5069cc93610c754a4088015",
            "<em>": "d1a25e1cb6b3d667b567323119f126f845c971df",
            "</em>": "851e149d4a4313c6016e73f719c269076790ab23",
            "<code>": "c1166919418e7c62a16b86662710541583068278",
            "</code>": "b7e364fd74d46f698c0f164988c382957c220c7c",
            "<s>": "03c7c0ace395d80182db07ae2c30f0341a739b1b",
            "</s>": "86029812940d86d63c5899ee5227cf94639408a7",
            "<strike>": "f0e25c74b67881c84327dc916c8c919f062c9003",
            "</strike>": "935f70051f605261d9f93948a5c3382f3a843596",
            "<del>": "8527a891e224136950ff32ca212b45bc93f69972",
            "</del>": "a992a007a4e77704231c285601a97cca4a70b768",
            "<pre>": "932162e70462a0f5d1a7599592ed51c41c4f8eb7",
            "</pre>": "e9e6f7c1fe77261334b414ae017288814903b225",
            "<u>": "764689e6705f61c6e7494bfa62688414325d8155",
            "</u>": "8a048b284925205d3187f8b04625a702150a936f",
        }

        REVERSE_TAG_MAP = {
            "40bd001563085fc35165329ea1ff5c5ecbdbbeef": "<b>",
            "c591326762260728871710537179fabf75973234": "</b>",
            "ef0b585e265b5287aa6d26a6860e0cd846623679": "<strong>",
            "e882cf5c82a930662f17c188c70ade885c55c607": "</strong>",
            "497603a6c32112169ae39a79072c07e863ae3f7a": "<i>",
            "0784921025d4c05de5069cc93610c754a4088015": "</i>",
            "d1a25e1cb6b3d667b567323119f126f845c971df": "<em>",
            "851e149d4a4313c6016e73f719c269076790ab23": "</em>",
            "c1166919418e7c62a16b86662710541583068278": "<code>",
            "b7e364fd74d46f698c0f164988c382957c220c7c": "</code>",
            "03c7c0ace395d80182db07ae2c30f0341a739b1b": "<s>",
            "86029812940d86d63c5899ee5227cf94639408a7": "</s>",
            "f0e25c74b67881c84327dc916c8c919f062c9003": "<strike>",
            "935f70051f605261d9f93948a5c3382f3a843596": "</strike>",
            "8527a891e224136950ff32ca212b45bc93f69972": "<del>",
            "a992a007a4e77704231c285601a97cca4a70b768": "</del>",
            "932162e70462a0f5d1a7599592ed51c41c4f8eb7": "<pre>",
            "e9e6f7c1fe77261334b414ae017288814903b225": "</pre>",
            "764689e6705f61c6e7494bfa62688414325d8155": "<u>",
            "8a048b284925205d3187f8b04625a702150a936f": "</u>",
        }

        def replace_tags_with_hashes(text):
            for tag, tag_hash in TAG_MAP.items():
                text = text.replace(tag, tag_hash)
            return text

        def replace_hashes_with_tags(text):
            for tag_hash, tag in REVERSE_TAG_MAP.items():
                text = text.replace(tag_hash, tag)
            return text

        text = replace_tags_with_hashes(text)
        text = re.sub(r'(?<=\|)(.*?)(?=\|)', lambda match: match.group(1).replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;'), text)
        text = replace_hashes_with_tags(text)

        return text
    except Exception as unknown:
        print(unknown)
        return original_text
    





def markdown_to_html(text: str) -> str:
    # переделывает маркдаун от чатботов в хтмл для телеграма
    # сначала делается полное экранирование
    # затем меняются маркдаун теги и оформление на аналогичное в хтмл
    # при этом не затрагивается то что внутри тегов код, там только экранирование
    # латекс код в тегах $ и $$ меняется на юникод текст


    # Словарь подстрочных символов
    subscript_map = {
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅',
        '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
        'a': 'ₐ',
        # 'b': '♭', 
        'c': '꜀',
        # 'd': 'ᑯ',
        'e': 'ₑ',
        # 'f': '⨍',
        'g': '₉',
        'h': 'ₕ',
        'i': 'ᵢ',
        'j': 'ⱼ',
        'k': 'ₖ',
        'l': 'ₗ',
        'm': 'ₘ',
        'n': 'ₙ',
        'o': 'ₒ',
        'p': 'ₚ',
        # 'q': '૧',
        'r': 'ᵣ',
        's': 'ₛ',
        't': 'ₜ',
        'u': 'ᵤ',
        'v': 'ᵥ',
        # 'w': 'w',
        'x': 'ₓ',
        'y': 'ᵧ',
        'z': '₂'
    }

    # Словарь надстрочных символов
    superscript_map = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵',
        '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
        'a': 'ᵃ',
        'b': 'ᵇ',
        'c': 'ᶜ',
        'd': 'ᵈ',
        'e': 'ᵉ',
        'f': 'ᶠ',
        'g': 'ᵍ',
        'h': 'ʰ',
        'i': 'ⁱ',
        'j': 'ʲ',
        'k': 'ᵏ',
        'l': 'ˡ',
        'm': 'ᵐ',
        'n': 'ⁿ',
        'o': 'ᵒ',
        'p': 'ᵖ',
        'q': '𐞥', 
        'r': 'ʳ',
        's': 'ˢ',
        't': 'ᵗ',
        'u': 'ᵘ',
        'v': 'ᵛ',
        'w': 'ʷ',
        'x': 'ˣ',
        'y': 'ʸ',
        'z': 'ᶻ'
    }

    # экранируем весь текст для html
    text = html.escape(text)

    # заменяем странный способ обозначения кода когда идет 0-6 пробелов в начале потом ` или `` или ``` и название языка
    pattern = r"^ {0,6}`{1,3}(\w+)\n(.*?)\n  {0,6}`{1,3}$"
    # replacement = r"```\1\n\2\n```"
    replacement = lambda match: f"```{match.group(1)}\n{re.sub(r'^ {1,6}', '', match.group(2), flags=re.MULTILINE)}\n```"
    text = re.sub(pattern, replacement, text, flags=re.MULTILINE | re.DOTALL)


    # найти все куски кода между ``` и заменить на хеши
    # спрятать код на время преобразований
    matches = re.findall('```(.*?)```\n', text, flags=re.DOTALL)
    list_of_code_blocks = []
    for match in matches:
        random_string = str(hash(match))
        list_of_code_blocks.append([match, random_string])
        text = text.replace(f'```{match}```', random_string)

    matches = re.findall('```(.*?)```', text, flags=re.DOTALL)
    for match in matches:
        random_string = str(hash(match))
        list_of_code_blocks.append([match, random_string])
        text = text.replace(f'```{match}```', random_string)

    # замена тегов <sub> <sup> на подстрочные и надстрочные символы
    text = re.sub(r'&lt;sup&gt;(.*?)&lt;/sup&gt;', lambda m: ''.join(superscript_map.get(c, c) for c in m.group(1)), text)
    text = re.sub(r'&lt;sub&gt;(.*?)&lt;/sub&gt;', lambda m: ''.join(subscript_map.get(c, c) for c in m.group(1)), text)

    # тут могут быть одиночные поворяющиеся `, меняем их на '
    text = text.replace('```', "'''")

    matches = re.findall('`(.*?)`', text)
    list_of_code_blocks2 = []
    for match in matches:
        random_string = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
        list_of_code_blocks2.append([match, random_string])
        text = text.replace(f'`{match}`', random_string)

    # меняем латекс выражения
    text = replace_latex(text)

    # переделываем списки на более красивые
    text = re.sub(r"^(\s*)\*\s", r"\1• ", text, flags=re.MULTILINE)
    text = re.sub(r"^(\s*)-\s", r"\1– ", text, flags=re.MULTILINE)

    # 1,2,3,4 # в начале строки меняем всю строку на жирный текст
    text = re.sub(r"^(?:\.\s)?#(?:#{0,})\s(.*)$", r"<b>\1</b>", text, flags=re.MULTILINE)  # 1+ hashes

    # цитаты начинаются с &gt; их надо заменить на <blockquote></blockquote>
    # &gt; должен быть либо в начале строки, либо сначала пробелы потом &gt;
    # если несколько подряд строк начинаются с &gt; то их всех надо объединить в один блок <blockquote>
    def process_quotes(text):
        # Разбиваем текст на строки
        lines = text.split('\n')
        result = []
        quote_lines = []
        
        for line in lines:
            # Проверяем, является ли строка цитатой (с учетом пробелов в начале)
            if re.match('^\s*&gt;\s*(.*)$', line):
                # Извлекаем текст после &gt;
                quote_content = re.sub('^\s*&gt;\s*(.*)$', '\\1', line)
                quote_lines.append(quote_content)
            else:
                # Если накопились цитаты, добавляем их в результат
                if quote_lines:
                    quote_text = '\n'.join(quote_lines)
                    result.append(f'<blockquote>{quote_text}</blockquote>')
                    quote_lines = []
                result.append(line)
        
        # Добавляем оставшиеся цитаты в конце текста
        if quote_lines:
            quote_text = '\n'.join(quote_lines)
            result.append(f'<blockquote>{quote_text}</blockquote>')
        
        return '\n'.join(result)

    text = process_quotes(text)


    # заменить двойные и тройные пробелы в тексте (только те что между буквами и знаками препинания)
    text = re.sub(r"(?<=\S) {2,}(?=\S)", " ", text)



    # First handle _*text*_ pattern (italic-bold combined)
    text = re.sub(r"(?<!\w)_\*([^\n\s].*?[^\n\s])\*_(?!\w)", r"<i><b>\1</b></i>", text)

    # Handle **_text_** pattern (bold-italic combined)
    text = re.sub(r"\*\*_(.+?)_\*\*", r"<b><i>\1</i></b>", text)

    # Handle _**text**_ pattern (italic-bold combined)
    text = re.sub(r"_\*\*(.+?)\*\*_", r"<i><b>\1</b></i>", text)

    # Handle *_text_* pattern (bold-italic combined)
    text = re.sub(r"\*_(.+?)_\*", r"<i><b>\1</b></i>", text)

    # Handle standalone bold (**text**)
    text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'^\*\*(.*?)\*\*$', r'<b>\1</b>', text, flags=re.MULTILINE | re.DOTALL)

    # Handle standalone italics (_text_ or *text*)
    text = re.sub(r"(?<!\w)_([^\n\s_*][^\n*_]*[^\n\s_*])_(?!\w)", r"<i>\1</i>", text)
    text = re.sub(r"(?<!\w)\*(?!\s)([^\n*]+?)(?<!\s)\*(?!\w)", r"<i>\1</i>", text)



    # 2 _ в <i></i>
    text = re.sub('\_\_(.+?)\_\_', '<i>\\1</i>', text)
    text = re.sub(r'^\_\_(.*?)\_\_$', r'<i>\1</i>', text, flags=re.MULTILINE | re.DOTALL)

    # Замена _*текст*_ на <i>текст</i>
    text = re.sub(r"(?<!\w)_\*([^\n\s].*?[^\n\s])\*_(?!\w)", r"<i>\1</i>", text)

    # Замена ~~текст~~ на <s>текст</s>
    text = re.sub(r"(?<!\w)~~(?!\s)([^\n*]+?)(?<!\s)~~(?!\w)", r"<s>\1</s>", text)

    # Замена ||текст|| на <tg-spoiler>текст</tg-spoiler>
    text = re.sub(r"(?<!\w)\|\|(?!\s)([^\n*]+?)(?<!\s)\|\|(?!\w)", r"<tg-spoiler>\1</tg-spoiler>", text)

    # замена <b><i> ... </b></i> на <b><i> ... </i></b>
    text = re.sub(r"<b><i>(.+?)</b></i>", r"<b><i>\1</i></b>", text)
    text = re.sub(r"<i><b>(.+?)</i></b>", r"<i><b>\1</b></i>", text)


    # меняем маркдаун ссылки на хтмл
    text = re.sub('''\[(.*?)\]\((https?://\S+)\)''', r'<a href="\2">\1</a>', text)

    # меняем все ссылки на ссылки в хтмл теге кроме тех кто уже так оформлен
    # а зачем собственно? text = re.sub(r'(?<!<a href=")(https?://\S+)(?!">[^<]*</a>)', r'<a href="\1">\1</a>', text)

    # хз откуда это
    text = text.replace('&#x27;', "'")
    text = text.replace('   #x27;', "'")
    text = text.replace('#x27;', "'")

    # меняем таблицы до возвращения кода
    text = replace_tables(text)

    # меняем обратно хеши на блоки кода
    for match, random_string in list_of_code_blocks2:
        # new_match = html.escape(match)
        new_match = match
        text = text.replace(random_string, f'<code>{new_match}</code>')

    # меняем обратно хеши на блоки кода
    for match, random_string in list_of_code_blocks:
        new_match = match
        text = text.replace(random_string, f'<code>{new_match}</code>')

    text = replace_code_lang(text)

    text = text.replace('<pre><code class="language-plaintext">\n<pre><code>', '<pre><code class="language-plaintext">')

    # убрать 3 и более пустые сроки подряд (только после блоков кода или любых тегов)
    def replace_newlines(match):
        return '\n\n'
    text = re.sub(r"(?<!<pre>)(?<!<code>)\n{3,}(?!</code>)(?!</pre>)", replace_newlines, text, flags=re.DOTALL)
    text = re.sub(r"pre>\n{2,}", "pre>\n", text)

    text = text.replace('\n</code></pre>\n</code>', '\n</code></pre>')

    return text


'''
<<<========================== WARNING ==========================>>>
All code in this file was taken from https://github.com/theurs/tb1.
It's unreadable, I don't understand it, but it works perfectly.
<<<========================== WARNING ==========================>>>
'''