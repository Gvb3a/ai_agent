from datetime import datetime
from typing import Literal
import asyncio

if __name__ == '__main__' or '.' not in __name__:
    from api import llm_api, calculator, wolfram_short_answer, wolfram_full_answer, google_short_answer, google_full_answer, google_image, youtube_sum, latex_expression_to_png
    from log import log

else:
    from .api import llm_api, calculator, wolfram_short_answer, wolfram_full_answer, google_short_answer, google_full_answer, google_image, youtube_sum, latex_expression_to_png
    from .log import log


system_prompt = '''You are a helpful ai agent with tools. You can use WolframALpha, Google, Search image, Summarize YouTube videos, Run python code and Compilate LaTeX dpocument. You are a Telegram bot providing the best answers. User does not see system message. Don't be afraid to use LaTeX in $$, they will all compile

To run the code, you must write it in ```python<code>``` and ask the user to click the button below the message to execute the. Only the first block of code will be executed. Available matplotlib. Write python code ONLY if this necessary. If you write a LaTeX document (in ```latex<document>```) you should also ask the user to compile it and he will get a pdf.'''


# TODO: funct that works with files
functions = { 
    'wolfram_short_answer': {
        'function': wolfram_short_answer,
        'description': 'For complex calculations, solving difficult equations and up-to-date information (e.g., weather, exchange rates, today date, time and etc). Don\'t use it for a conventional solution',
        'output_file': False
    },
    'wolfram_full_answer': { 
        'function': wolfram_full_answer,
        'description': 'Full Wolfram Alpha answer with pictures and a lot of information',
        'output_file': True
    },
    'google_short_answer': {
        'function': google_short_answer,
        'description': 'Use if you need to get revelant information from the internet. It\'s important to ask the question well (e. g "Who won on 2024 Olympic" -> "Which country won the most medals 2024 olympics")',
        'output_file': False
    },
    'google_full_answer': {   # TODO
        'function': google_full_answer,
        'description': 'For queries needing full-text information from the internet (e.g., entire lyrics or detailed articles). Don\'t use it for information you know.',
        'output_file': False
    },
    'google_image': {
        'function': google_image,
        'description': 'Pictures that pop up when you search. Use when the user asks to find a picture',
        'output_file': True
    },
    'youtube_sum': {   # TODO: ask que
        'function': youtube_sum,
        'description': 'Summarizes YouTube videos. Enter link in input',
        'output_file': False
    },
    'latex_expression_to_png': {
        'function': latex_expression_to_png,
        'description': 'Converts LaTeX expressions (what\'s in $$) to png. Enter only LaTeX expression in input. When user says compile this expression then use this tool',
        'output_file': True
    }
}

prompt_for_chatbot_assistant = 'You are the chatbot\'s assistant, in charge of choosing the right tool for each request. Available functions:\n\n'

for items in functions.items():
    prompt_for_chatbot_assistant += f'{items[0]}: {items[1]["description"]}\n'

prompt_for_chatbot_assistant += f"""\nAnswer in the following format:

Thought: You should always think about what to do. What the user wants to see, what is the best tool to use and what inputs to use? Think only in English

<function_name>: <function_input>


You can call multiple functions (unless the model herself is unable to answer), each time spelling out the names of the function and the query for it. You can call the same function multiple times, so don't be afraid to split questions into the same function. Don't forget to convert the queries, and also avoid obscene queries in functions. Use tools only when they are needed. You should not call functions during a normal conversation (or if the model can answer itself).
USE TOOLS ONLY IF NECESSARY.

You'll be given a message history."""



# TODO: files to context, auto-translate
def llm_select_tool(messages: list | str, files: list = [], provider: Literal['groq', 'google'] = 'google') -> list:
    # TODO: multiple arguments for a function
    if type(messages) == list:
        user_message = 'History:'+'\n'.join(f'{i["role"]}: {i["content"]}' for i in messages[:-1])
        user_message += f'\nUser ask: {messages[-1]["content"]}'
    else:
        user_message = messages

    message_history = [
        {'role': 'system',
         'content': prompt_for_chatbot_assistant},
        {
        'role': 'user',
        'content': user_message
        }
    ]
    llm_answer = llm_api(messages=message_history, files=files, provider=provider) + '\n'
    answers = llm_answer.split('\n')
    tools = []
    for answer in answers:
        try:
            func_name = answer.split(':')[0]
            func_input = ':'.join(answer.split(':')[1:])
        except Exception as e:
            continue
        
        func_name = func_name.strip().lower()
        if func_name in functions:
            tools.append({'func_name': func_name, 'func_input': func_input.strip()})

    log(f'tools: {tools}, user_message: {user_message}')
    return tools



async def execute_tool(func_name, func_input: str):
    if asyncio.iscoroutinefunction(func_name):
        return await func_name(func_input)
    else:
        return await asyncio.to_thread(func_name, func_input)


async def llm_use_tool(tools: list[dict]) -> tuple[str, list]:
    
    tasks = [
        execute_tool(functions[tool['func_name']]['function'], tool['func_input']) for tool in tools
    ]

    results = await asyncio.gather(*tasks)

    str_results = []
    images = []
    for i, func_result in enumerate(results):
        if type(func_result) in [str, None]:
            str_results.append(f"{tools[i]['func_name']}({tools[i]['func_input']}): {func_result}")
        else:
            str_results.append(f"{tools[i]['func_name']}({tools[i]['func_input']}): {func_result[0]}")
            images.extend(func_result[1])

    result = '\n'.join(str_results)
    log(f'{result}, {images}')
    
    return result, images

# TODO: FILES
def llm_full_answer(messages: list, files: list = [], provider: Literal['groq', 'google'] = 'groq') -> str:

    tools = llm_select_tool(messages=messages)
    tool_result, images = asyncio.run(llm_use_tool(tools=tools))  # TODO: await


    if type(messages) == str:
        user_message = messages
        messages = [{'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}]
    else:
        messages.insert(0, {'role': 'system', 'content': system_prompt})

    if bool(tool_result) + bool(images):
        messages.append({'role': 'assistant', 'content': 'tool result:\n' + tool_result})
        
    answer = llm_api(messages=messages, files=files, provider=provider)

    log(f'answer: {answer}, tool: {tool_result}, images: {images}')

    return answer
