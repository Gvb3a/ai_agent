# https://www.latex-project.org/. Used https://latex.codecogs.com/ and https://latexonline.cc/
import hashlib
import requests
from urllib.parse import quote
from .file_utils import download_images
from ..llm.llm import llm_api
from ...config.logger import logger


def latex_expression_to_png(expression: str, size: int = 400):
    '''Converts a LaTeX expression to a PNG image with https://latex.codecogs.com/'''
    try:
        expression = expression.strip('$')
        link = 'https://latex.codecogs.com/png.image?\\dpi{' + str(size) + '}' + expression.replace(' ', '%20')
        response = requests.get(link)
        file_name = hashlib.md5(expression.encode()).hexdigest() + '.png'
        if response.status_code == 200:
            with open(file_name, 'wb') as f:
                f.write(response.content)
            logger.info(expression)
            return f'A rendering of the expression {expression} will be added to the answer', [file_name]
        else:
            logger.error(expression)
            return None
    except:
        logger.error(expression, exc_info=True)
        return None


async def async_expressions_to_png(expressions: list[str], size: int = 400):
    '''Converts a list of LaTeX expressions to PNG images asynchronously.'''
    try:
        links = []
        for expression in expressions:
            if type(expression) != str:
                l = [i for i in expression if i]
                expression = l[0]
            expression = expression.strip('$')
            if len(expression) <= 3:
                continue
            link = 'https://latex.codecogs.com/png.image?\\dpi{' + str(size) + '}' + expression.replace(' ', '%20')
            links.append(link)
        logger.info(f'expressions: {expressions}')
        return await download_images(links)
    except Exception as e:
        logger.error(f'error: {e}', exc_info=True)
        return []
    

def latex_to_pdf(content: str, recursion_turn: int = 1) -> str | None:
    '''Converts LaTeX content to a PDF file. If the content is invalid LaTeX, it will try to fix it with llm_api'''
    if '\\begin{document}' not in content:
        preambula = '''\\documentclass[a4paper]{article}
\\usepackage[english,russian]{babel}
\\usepackage[utf8]{inputenc}
\\usepackage{geometry}
\\geometry{a4paper, left=15mm, right=15mm, top=15mm, bottom=17mm}
\\usepackage{amsmath, amssymb, amsfonts}
'''
        content = preambula + '\\begin{document}\n' + content + '\n\\end{document}'
    if recursion_turn > 3:
        return None
    
    link = 'https://latexonline.cc/compile?text=' + quote(content)
    response = requests.get(link)
    file_name = hashlib.md5(content.encode()).hexdigest() + '.pdf'
    if response.status_code == 200:
        with open(file_name, 'wb') as f:
            f.write(response.content)
        logger.info(content)
        return file_name
    else:
        logger.error(f'Error: {response.text}, recursion_turn: {recursion_turn}, content: {content}')
        prompt = 'You are a LaTeX expert. You have to fix the LaTeX Document so that the error does not occur (if the error is very unclear, you can remove the part of the text with the error). '\
                 'Your whole reply will go in the reply, so you can write your thoughts in the comments (after %), nobody will see them. '\
                f'Error: {response.text}\n\nText:{content}'
        answer = llm_api(prompt)
        if answer.startswith('```latex'):
            answer = answer[8:-4]
        elif answer.startswith('```'):
            answer = answer[3:-4]
        logger.info(f'Ask llm: {answer}. ')
        return latex_to_pdf(answer, recursion_turn+1)
    

def text_to_pdf_document(text: str):
    '''Converts a text to a PDF file using LaTeX. Using llm_api and latex_to_pdf'''
    prompt = "You are a LaTeX expert. Your task is to convert this text in MarkDown markup into a LaTeX document. You don't have to cause an error.  "\
             "Tips: use in preambula \\documentclass[a4paper]{article}, \\usepackage[english,russian]{babel}, \\usepackage[utf8]{inputenc}, \\usepackage{geometry}, \\geometry{a4paper, left=15mm, right=15mm, top=15mm, bottom=17mm}, \\usepackage{amsmath, amssymb}. You can add your own."\
             "You encapsulate EACH math equation IN $$ and use LaTeX. If something like V2 or T₃ occurs in the text, convert it to V_2 and T_3, Δ to \\Delta and etc. For bold (**) use \\textbf{}, for bullet list use itemize and so on. "\
            f"Text:\n{text}"
    
    
    answer = llm_api(prompt).strip()
    
    if answer.startswith('```latex'):
        answer = answer[8:-4]
    elif answer.startswith('```'):
        answer = answer[3:-4]

    file_name = latex_to_pdf(answer)
    logger.info(f'text: {text}, answer: {answer}', error=not bool(file_name))
    return file_name