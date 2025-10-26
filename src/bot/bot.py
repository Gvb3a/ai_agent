import os
import re
import asyncio
from time import sleep
from collections import Counter
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup

from .formatter import markdown_to_html, split_html
from ..agent.agent import system_prompt, llm_select_tool, llm_use_tool
from ..agent.llm.llm import llm_api
from ..agent.llm.groq import groq_api, groq_api_compound
from ..agent.tools.wolfram import wolfram_simple_api
from ..agent.tools.code_interpreter import code_interpreter
from ..agent.tools.translate import detect_language, translate
from ..agent.tools.latex import latex_to_pdf, async_expressions_to_png
from ..agent.tools.file_utils import files_to_text, speech_recognition, merge_pngs_vertically
from .database import (
    utc_time,
    text_to_hash,
    sql_check_user,
    sql_select_history,
    sql_insert_message,
    sql_clear_user_history,
    sql_get_message_by_hash,
)
from ..config.logger import logger
from ..config.config import load_config, Config
    

config: Config = load_config()
bot_token = config.tg_bot.token


class FSM(StatesGroup):
    processing = State()
    wolfram = State()
    groq = State()
    gpt_oss = State()
    gemini = State()


bot = Bot(token=str(bot_token))
dp = Dispatcher()


async def download_file_for_id(file_id, extension):

    file = await bot.get_file(file_id)
    file_path = str(file.file_path)
    file_name = f'{text_to_hash(utc_time())}.{extension}'
    await bot.download_file(file_path, file_name)

    return file_name


@dp.message(CommandStart())  # /start command handler
async def start_command_handler(message: Message) -> None:
    user_language_code = message.from_user.language_code
    start_message = config.tg_bot.messages.start.get(user_language_code, config.tg_bot.messages.start['en'])
    await message.answer(start_message, parse_mode='Markdown')
    logger.info(f'{message.from_user.full_name}({message.from_user.username})')


help_message = f'''[Code source](https://github.com/Gvb3a/assistant)\n\

Model: `gemini-2.0-flash-exp` or `llama-3.3-70b`

Tools: 
 • *WolframAlpha*: An incredibly powerful calculator. It can solve any equation, calculate huge numbers, give up-to-date information and much more. With `wolfram_full_answer` you and the model will be presented with the full WolframAlpha answer. For simple request-response will use `wolfram_alpha_short_answer`.
 • *Google*: The model can access the internet to get up-to-date information. `google_short_answer` gives a short and quick answer to the model, and `google_full_answer` starts a process in which the model reads 3 links in Google. There is also an option to search for images with `google_images`
 • *LaTeX*: LaTeX is a language for mathematical expressions. The bot automatically converts it from unreadable text into understandable text in messages, but with `latex_expression_to_png` you can get a picture of the expression. Just ask to compile the expression into a picture. \
The bot also supports the compilation of LaTeX documents. If the message contains latex code, a button with the inscription `Render latex` will appear below the message. After clicking, you will be sent a pdf file
 • *Python*: You can run python code that the agent will write. Just click the corresponding button. Running the code greatly expands the capabilities of llm for issuing answers.
 • *Translate*: If the model has answered in a language other than yours, you will be able to translate the answer. This will allow you to speak unpopular languages ​​+ it is no secret that the model thinks better in English.
 • *Youtube*: With `youtube_sum` you can send a link to a YouTube video and he will retell it to you. In the future, you can ask questions.
 • *IMDB*: `imdb_api` will give the model an answer from the largest library of films. This will help to find out the year of release, actors, genres, ratings, reviews, etc. 
 • *Image Generate*: Thanks to Hugging Face, the bot can generate images using Flux. Function name: `generate_image`. Generation takes about a minute.

Support: @{config.tg_bot.support_tg}
'''
@dp.message(Command('help'))
async def help_command_handler(message: Message) -> None:
    user_language_code = message.from_user.language_code
    if user_language_code != 'en':
        inline_keyboard= [InlineKeyboardButton(text=f'Translate to {user_language_code} 📖', callback_data=f'translate_help_message-{user_language_code}')]
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[inline_keyboard])
    else:
        inline_keyboard = None

    await message.answer(help_message, parse_mode='Markdown', disable_web_page_preview=True, reply_markup=inline_keyboard)
    logger.info(f'{message.from_user.full_name}({message.from_user.username})')


ADMIN_IDS = config.tg_bot.admin_ids
@dp.message(Command('log'))
async def log_command_handler(message: Message) -> None:
    if message.from_user.id in ADMIN_IDS:
        try:
            await message.answer_document(FSInputFile(config.logs.log_path))
            await message.answer_document(FSInputFile(config.logs.errors_log_path))
        except Exception as e:
            await message.reply(f'Error: {e}')
        logger.info('Admin used /log command')
    else:
        logger.warning(f'{message.from_user.full_name}({message.from_user.id}) try use /log command')
        await message.reply('You are not an admin')


@dp.message(StateFilter(FSM.processing))
async def processing_message_handler(message: Message, state: FSMContext) -> None:
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f'Cancel generation', callback_data=f'clear_state')]])
    await message.reply(f'If you get stuck, write to [admin](https://t.me/{config.tg_bot.support_tg}) or click the button below and wait 10 seconds', reply_markup=inline_keyboard, parse_mode='Markdown')
    logger.warning(f'{message.from_user.full_name}({message.from_user.username}) - stuck')


@dp.callback_query(F.data == 'clear_state')
async def clear_state_callback(callback: CallbackQuery, state: FSMContext) -> None:
    logger.warning(f'{callback.from_user.full_name}({callback.from_user.username}) - button clear state')
    sleep(10)
    await state.clear()
    await callback.answer('State cleared')


@dp.message(Command('clear'))
async def clear_command_handler(message: Message) -> None:
    sql_check_user(message.from_user.full_name, message.from_user.username, message.from_user.id)
    sql_clear_user_history(message.from_user.id)
    await message.answer("Your history has been cleared.")
    logger.info(f'{message.from_user.full_name}({message.from_user.username}) - clear history')


@dp.message(Command('default'))
async def default_command_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Now you will be answered by a standard agent. Very smart and functional, but slow.")
    logger.info(f'{message.from_user.full_name}({message.from_user.username}) - default state')
    
    
@dp.message(Command('wolfram'))
async def wolfram_command_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state == FSM.wolfram.state:
        await state.clear()
        await message.answer("Wolfram mode deactivated.")
    else:
        await state.set_state(FSM.wolfram)
        await message.answer("All your questions will be answered using WolframAlpha. If you want to switch back to normal mode, type /wolfram.")
    logger.info(f'{message.from_user.full_name}({message.from_user.username}) - {current_state}')


@dp.message(Command('groq'))
async def groq_command_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state == FSM.groq.state:
        await state.clear()
        await message.answer("Groq agent deactivated.")
    else:
        await state.set_state(FSM.groq)
        await message.answer("Now you will be assisted by Groq — a fast and stable agent with access to *Web Search*, *Code Execution* and *Website Visits*. Does not support images, but supports documents and audio. To switch back, type /groq.",
                             parse_mode='Markdown')
    logger.info(f'{message.from_user.full_name}({message.from_user.username}) - {current_state}')


@dp.message(Command('gpt_oss'))
async def gpt_oss_command_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state == FSM.gpt_oss.state:
        await state.clear()
        await message.answer("GPT-OSS model deactivated.")
    else:
        await state.set_state(FSM.gpt_oss)
        await message.answer("Now you will be assisted by GPT-OSS — OpenAI's fast and intelligent model without access to tools. Does not support images, but supports documents and audio. To switch back, type /gpt_oss.")
    logger.info(f'{message.from_user.full_name}({message.from_user.username}) - {current_state}')


@dp.message(Command('gemini'))
async def gemini_command_handler(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state == FSM.gemini.state:
        await state.clear()
        await message.answer("Gemini model deactivated.")
    else:
        await state.set_state(FSM.gemini)
        await message.answer("Now you will be assisted by Gemini — Google's smartest model. To switch back, type /gemini.")
    logger.info(f'{message.from_user.full_name}({message.from_user.username}) - {current_state}')



@dp.message(StateFilter(FSM.wolfram))
async def wolfram_message_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(FSM.processing)
    if message.photo:
        await message.answer("Processing your WolframAlpha query... Image recognition will take time.")
        file = await bot.get_file(message.photo[-1].file_id)
        file_path = file.file_path
        file_name = file.file_path.split('/')[-1]
        await bot.download_file(file_path, file_name)

        input_files = [file_name]
        system_prompt = "You are a helpful assistant who can turn images into a query for Wolfram Alpha. In your answer, provide ONLY the text of the expression, without any additional comments. If the image contains a mathematical expression, write it down exactly as it appears. If there are several expressions in the picture, write only the first one."
        prompt = f"Give a query for Wolfram Alpha from this image"
        query = llm_api(messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': prompt}], files=input_files)
    else:
        await message.answer("Processing your WolframAlpha query... ")
        query = message.text
    response = wolfram_simple_api(query)
    temp_message_id = message.message_id + 1
    if response is None:
        await bot.edit_message_text(chat_id=message.chat.id, message_id=temp_message_id, text="WolframAlpha couldn't process your query directly. Fixing...")
        prompt = f"Fix this query for Wolfram Alpha: {query}."
        system_prompt = "You are a helpful assistant that corrects queries for Wolfram Alpha. In your response, provide the corrected query ONLY"
        new_query = llm_api(messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': prompt}], files=[])
        response = wolfram_simple_api(new_query)

    await bot.delete_message(chat_id=message.chat.id, message_id=temp_message_id)
    if isinstance(response, str) and (response.endswith('.png') or response.endswith('.jpg') or response.endswith('.jpeg') or response.endswith('.webp')):
        await message.answer_photo(FSInputFile(response))
    elif isinstance(response, str) and (response.startswith('http://') or response.startswith('https://')):
        await message.answer_photo(response)
    else:
        await message.answer("Sorry, I couldn't process your query.")

    logger.info(f'{message.from_user.full_name}({message.from_user.username}) - {query}')
    await state.set_state(FSM.wolfram)


@dp.message(StateFilter(FSM.groq))
@dp.message(StateFilter(FSM.gpt_oss))
async def groq_and_gpt_oss_message_handler(message: Message, state: FSMContext) -> None:
    previous_state = await state.get_state()
    await state.set_state(FSM.processing)
    input_files = []
    message_to_delete = message.message_id + 1
    if message.photo:
        await message.answer("This model does not support images.")
        await state.set_state(previous_state)
        return
    elif message.document:
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_name = file.file_path.split('/')[-1]
        await bot.download_file(file_path, file_name)
        input_files = [file_name]
        text = str(message.caption) if message.caption else 'Describe the document or answer a previous question'
        await message.answer('The document has been read ✅. Every time you ask for a document, you will need to send it.')
        message_to_delete += 1

    elif message.voice:
        await message.answer('Recognizing audio...')
        file_name = await download_file_for_id(file_id=message.voice.file_id, extension='mp3')
        text = speech_recognition(file_name=file_name).strip()
        os.remove(file_name)
        await bot.edit_message_text(chat_id=message.chat.id, message_id=message_to_delete, text=f'Recognized as "{text}"')
        message_to_delete += 1
    
    if message.text:
        text = str(message.text)
    await message.answer('⏳')

    messages = sql_select_history(id=message.from_user.id)
    messages.append({'role': 'user', 'content': text})
    sql_check_user(user_id=message.from_user.id, telegram_name=message.from_user.full_name, telegram_username=message.from_user.username)
    sql_insert_message(user_id=message.from_user.id, role='user', content=text)
    logger.info(f'New message by {message.from_user.full_name}. messages: {text}, files: {input_files}, state: {previous_state}')
    
    if previous_state == FSM.groq:
        answer, tools, time = groq_api_compound(messages=messages, files=input_files, only_answer=False)
    else: # elif previous_state == FSM.gpt_oss
        answer = groq_api(messages=messages, files=input_files)
        
    await bot.delete_message(chat_id=message.chat.id, message_id=message_to_delete)

    
    for part in split_html(markdown_to_html(answer)):
        try:
            await message.answer(part, parse_mode='HTML')
        except:
            inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Fix formatting', callback_data=f'fix_formatting')]])
            await message.answer(part, reply_markup=inline_keyboard)


    logger.info(f'Mode: {previous_state}. Answer to {message.from_user.full_name}({text}): {answer}')
    sql_insert_message(user_id=message.from_user.id, role='assistant', content=answer)

    if tools:
        counts = Counter()
        for entry in tools:
            tool_name = next(iter(entry))
            counts[tool_name] += 1
        parts = []
        for tool in sorted(counts):
            cnt = counts[tool]
            if cnt == 1:
                parts.append(f"`{tool}`")
            else:
                parts.append(f"`{tool}` (x{cnt})")
        model = f'**Used:** `groq/compound`'
        tools = '**Tools:** ' + ", ".join(parts)
        time = f'**Time:** {time}'
        await message.answer(markdown_to_html(f"{model}\n{tools}\n{time}"), parse_mode='HTML')  # TODO: settings: model (mini/normal), show this message, browser_auto

    await state.set_state(FSM.groq)


                



@dp.message(StateFilter(default_state))
async def message_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(FSM.processing)  # mark processing

    chat_id = message.chat.id
    user = message.from_user.full_name
    user_id =  message.from_user.id
    username = message.from_user.username
    message_id = message.message_id

    sql_check_user(user_id=user_id, telegram_name=user, telegram_username=username)

    temp_message_text = ['Selecting tool - 🔍', 'Using the tool - ⚙️', 'Generating response - 🤖']
    temp_message_id = message_id + 1

    # ======================= input =======================
    if message.voice:
        await message.reply('Recognizing audio...')
        file_name = await download_file_for_id(file_id=message.voice.file_id, extension='mp3')
        
        text = speech_recognition(file_name=file_name).strip()
        os.remove(file_name)
        
        temp_message_text[0] = temp_message_text[0][:-2] + '✅'
        await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text=f'Recognized: {text}')
        input_files = []
        temp_message_id += 1
    
    elif message.photo:
        await message.reply('Every time you ask a new image question, you will have to submit the image again.')
        file_id = message.photo[-1].file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_name = file.file_path.split('/')[-1]
        await bot.download_file(file_path, file_name)

        input_files = [file_name]

        text = str(message.caption) if message.caption else 'Describe the image'

        temp_message_id += 1

    elif message.document:
        await message.reply('Every time you ask a new document question, you will have to submit the document again.')
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        file_name = file.file_path.split('/')[-1]
        await bot.download_file(file_path, file_name)

        input_files = [file_name]

        text = str(message.caption) if message.caption else 'Describe the document or answer a previous question'

        temp_message_id += 1

    else:
        input_files = []

    if message.text:
        text = str(message.text)
    
    await message.reply('\n'.join(temp_message_text))
    # ======================= take history and files =======================
    messages = sql_select_history(id=user_id)
    messages.insert(0, {'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': text})
    sql_insert_message(user_id=user_id, role='user', content=text)
     
    for file in input_files:  # If the file is not a picture, convert the file to text and add it to the user message
        if not(file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.webp')):
            messages[-1]['content'] += f'\n\n{file}:\n{files_to_text(file)}'
            input_files.remove(file)

    logger.info(f'new message by {user}. messages: {text}, files: {input_files}')


    # ======================= select tool, use tool and get answer =======================
    loop = asyncio.get_running_loop()
    

    select_task = loop.run_in_executor(None, llm_select_tool, messages, input_files, 'google')
    api_task = loop.run_in_executor(None, llm_api, messages, input_files, 'google')

    tools = await select_task
    
    if tools == []:
        
        temp_message_text[0] = temp_message_text[0][:-2] + '✅'
        temp_message_text[1] = temp_message_text[1][:-2] + '✅'
        await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text='\n'.join(temp_message_text))
        answer = await api_task
        output_files = []
    else:
        temp_message_text[0] = temp_message_text[0][:-2] + '(' +','.join(set([i['func_name'] for i in tools])) + ')✅'
        await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text='\n'.join(temp_message_text))

        tool_result, output_files = await llm_use_tool(tools=tools)
        temp_message_text[1] = temp_message_text[1][:-2] + '✅'
        await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text='\n'.join(temp_message_text))

        messages.append({'role': 'system', 'content': 'tool result:\n' + tool_result})
        sql_insert_message(user_id=user_id, role='system', content='tool result:\n' + tool_result)
        
        answer = llm_api(messages=messages, files=input_files, provider='google')

    await bot.delete_message(chat_id=chat_id, message_id=temp_message_id)
    logger.info(f'answer to {user}({text}): {answer}')
    sql_insert_message(user_id=user_id, role='assistant', content=answer)

    # ======================= send files =======================
    output_files_to_delete = output_files.copy()
    while output_files:
        media_group = []

        for file in output_files[:9]:

            if file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.webp'):
                media = FSInputFile(file)
                media_group.append(InputMediaPhoto(media=media))
            else:
                document = FSInputFile(file)
                await bot.send_document(chat_id=chat_id, document=document)

        try:
            if media_group:
                await message.answer_media_group(media=media_group)
        except Exception as e:
            print('media group error', e)

        output_files = output_files[9:]

    # ======================= buttons =======================
    inline_keyboard = []
    message_hash = text_to_hash(answer)
    
    if '```python' in answer:
        inline_keyboard.append(InlineKeyboardButton(text='Run code ➡', callback_data=f'run_python_code-{message_hash}'))

    if '```latex' in answer:
        inline_keyboard.append(InlineKeyboardButton(text='Render latex ➡', callback_data=f'render_latex-{message_hash}'))
    
    latex_expressions = re.findall(r'\$\$(.*?)\$\$|\$(.*?)\$', answer, re.DOTALL) 

    user_text_language = detect_language(text)
    answer_text_language = detect_language(answer)
    if answer_text_language != user_text_language:
        inline_keyboard.append(InlineKeyboardButton(text=f'Translate to {user_text_language} 📖', callback_data=f'translate_message-{message_hash}-{user_text_language}'))

    user_language_code = message.from_user.language_code 
    if user_language_code != user_text_language:
        inline_keyboard.append(InlineKeyboardButton(text=f'Translate to {user_language_code} 📖', callback_data=f'translate_message-{message_hash}-{message.from_user.language_code}'))

    if inline_keyboard == []:
        inline_keyboard = None
    else:
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[inline_keyboard])
 

    # ======================= send answer =======================
    while answer:
        try:
            await message.answer(markdown_to_html(answer[:4000]), parse_mode='HTML', reply_markup=inline_keyboard)
            inline_keyboard = None
        except Exception as e:
            await message.answer(answer[:4000])
        answer = answer[4000:]

    # ======================= latex expressions in message to png =======================
    expressions = await async_expressions_to_png(latex_expressions)
    output_files_to_delete.extend(expressions)

    if expressions:
        merge_latex_image = merge_pngs_vertically(expressions)
        await message.answer_photo(FSInputFile(merge_latex_image))
        output_files_to_delete.append(merge_latex_image)
        


    # ======================= delete files =======================
    try:
        for file in output_files_to_delete:
            if not file.startswith('https:'):
                try:
                    os.remove(file)
                except:
                    os.remove(file.split('/')[-1])  

    except Exception as e:
        print(e)

    await state.clear()




# <======================== CALLBACKS ========================>
@dp.callback_query(F.data == 'fix_formatting')
async def callback_fix_formatting(callback: CallbackQuery):
    message = callback.message.text
    promt = '''You are a specialized HTML validator for Telegram messages. Your sole task is to fix incorrect HTML formatting in the text.

CRITICALLY IMPORTANT:
- Output ONLY the corrected HTML code, without explanations, comments, or additional text
- Your response will be sent directly to the user

TASKS:
1. Fix all broken HTML tags (unclosed, truncated, missing opening brackets)
2. Restore proper tag nesting
3. Ensure every opening tag has a closing tag
4. Preserve all original text and content without changes

SUPPORTED TELEGRAM TAGS:
<b>, <i>, <u>, <s>, <code>, <pre>, <a href="">, <tg-spoiler>

COMMON ERRORS TO FIX:
- `pre><code>` → `<pre><code>`
- `</pre>` without `</code>` → `</code></pre>`
- `<code` → `<code>`
- `b>text</b>` → `<b>text</b>`
- Tags truncated at message boundaries
- Incorrect closing order for nested tags

RULES:
✓ Preserve original text completely
✓ Fix only tag structure
✓ If tag is truncated at start - restore opening tag
✓ If tag is truncated at end - add closing tag
✓ Maintain proper nesting: <b><i>text</i></b> ✓, <b><i>text</b></i> ✗

RESPONSE FORMAT:
[Only corrected HTML, nothing else]

Text to fix:\n''' + message
    new_message = llm_api(promt)
    try:
        await callback.message.edit_text(new_message, parse_mode='HTML')
        await callback.answer()
    except Exception as e:
        try:
            await callback.message.answer(new_message, parse_mode='HTML')
        except Exception as e:
            await callback.answer('Nothing worked out')


@dp.callback_query(F.data[:17] == 'translate_message')
async def callback_translate_message(callback: CallbackQuery):
    'translate_message-{message_hash}-{user_text_language}'
    message_hash = callback.data.split('-')[1]
    user_text_language = callback.data.split('-')[2]

    text = sql_get_message_by_hash(message_hash)
    translated = translate(text, user_text_language)

    
    logger.info(f'translate_message - User: {callback.from_user.full_name}, message: {text}, translated: {translated}, message_hash: {message_hash}')
    while translated:
        try:
            await callback.message.answer(markdown_to_html(translated[:4000]), parse_mode='HTML')
        except:
            await callback.message.answer(translated[:4000])
        translated = translated[4000:]

     
    await callback.answer()


@dp.callback_query(F.data[:15] == 'run_python_code')
async def callback_run_code_in_message(callback: CallbackQuery):
    'callback: run_python_code-{message_hash}'

    message_hash = callback.data.split('-')[1]
    text = sql_get_message_by_hash(message_hash)

    try:
        code = text.split('```python')[1].split('```')[0]
    except:
        code = None

    if not code:
        await bot.send_message(chat_id=callback.from_user.id, text='No code found or error in the code')
        logger.error(f'User: {callback.from_user.full_name}, message: {text}')
        await callback.answer()
        return
    
    str_result, image = code_interpreter(code)

    if str_result.replace('\n', '') == '':
        str_result = 'no text output'
    
    if image:
        await bot.send_photo(chat_id=callback.from_user.id, photo=FSInputFile(image))
        os.remove(image)


    logger.info(f'User: {callback.from_user.full_name}, result: {str_result}, image: {bool(image)}, message_hash: {message_hash}, code: {code}')
    sql_insert_message(user_id=callback.from_user.id, role='system', content=f'The result of code execution that is visible to the user: {str_result}. \nif there\'s an image: {bool(image)}')

    while str_result:
        await bot.send_message(chat_id=callback.from_user.id, text=f'```output\n{str_result[:4000]}\n```', parse_mode='Markdown')
        str_result = str_result[4000:]
    
    callback.answer()
    


@dp.callback_query(F.data[:12] == 'render_latex')
async def callback_render_latex(callback: CallbackQuery):
    'callback: render_latex-{message_hash}'
    message_hash = callback.data.split('-')[1]
    text = sql_get_message_by_hash(message_hash)
    
    latex = re.findall(r'```latex\n(.*?)\n```', text, re.DOTALL)[0]
    
    file_name = latex_to_pdf(latex)
    if file_name:
        await callback.message.answer_document(document=FSInputFile(file_name))
        os.remove(file_name)
        logger.info(f'User: {callback.from_user.full_name}, latex: {latex}, message_hash: {message_hash}')
    else:
        logger.error(f'User: {callback.from_user.full_name}, latex: {latex}, message_hash: {message_hash}')
        await callback.message.answer('Error in latex rendering')
    sql_insert_message(user_id=callback.from_user.id, role='system', content=f'latex rendering result: {bool(file_name)}')
    await callback.answer()
    

@dp.callback_query(F.data[:22] == 'translate_help_message')
async def callback_render_latex(callback: CallbackQuery):
    language = callback.data.split('-')[1]
    translated = translate(text=help_message, target_language=language, source_language='en')

    logger.info(f'User: {callback.from_user.full_name}, language: {language}')

    try:
        await callback.message.answer(translated, parse_mode='Markdown')
    except:
        await callback.message.answer(translated)

    await callback.answer()



if __name__ == '__main__':
    logger.info('Bot is launched')
    dp.run_polling(bot)
