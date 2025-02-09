from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
import os
from dotenv import load_dotenv
import re


if __name__ == '__main__' or '.' not in __name__:
    from api import speech_recognition, llm_api, files_to_text, code_interpreter, detect_language, translate, latex_to_pdf, async_expressions_to_png, merge_pngs_vertically
    from llm_answer import system_prompt, llm_select_tool, llm_use_tool
    from sql import sql_check_user, sql_select_history, sql_insert_message, sql_get_message_by_hash
    from sql import utc_time, text_to_hash
    from log import log
    from magic import markdown_to_html
else:
    from .api import speech_recognition, llm_api, files_to_text, code_interpreter, detect_language, translate, latex_to_pdf, async_expressions_to_png, merge_pngs_vertically
    from .llm_answer import system_prompt, llm_select_tool, llm_use_tool
    from .sql import sql_check_user, sql_select_history, sql_insert_message, sql_get_message_by_hash
    from sql import utc_time, text_to_hash
    from .log import log
    from .magic import markdown_to_html
    

load_dotenv()
bot_token = os.getenv('BOT_TOKEN')


class FSM(StatesGroup):
    processing = State()


bot = Bot(token=str(bot_token))
dp = Dispatcher()


async def download_file_for_id(file_id, extension):

    file = await bot.get_file(file_id)
    file_path = str(file.file_path)
    file_name = f'{text_to_hash(utc_time)}.{extension}'
    await bot.download_file(file_path, file_name)

    return file_name


@dp.message(CommandStart())  # /start command handler
async def start_command_handler(message: Message) -> None:
    await message.answer('Hi! I am an AI agent that can search for information on the internet, use a WolfraAlpha (calculator), summarize youtube videos, compile latex files and images and execute python code. How can I help you today?  \n\n[GitHub](https://github.com/Gvb3a/assistant)', parse_mode='Markdown')
    log(f'{message.from_user.full_name}({message.from_user.username})')


help_message = '''[Code source](https://github.com/Gvb3a/assistant)\n\

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
 • *Image Generate*: Thanks to Hugging Face, the bot can generate images using Flux. Function name: `generate_image`.

Admin: @gvb3a
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
    log(f'{message.from_user.full_name}({message.from_user.username})')


ADMIN_ID = os.getenv('ADMIN_ID')
@dp.message(Command('log'))
async def log_command_handler(message: Message) -> None:
    if message.from_user.id == int(ADMIN_ID):
        try:
            await message.answer_document(FSInputFile('agent_log.log'))
        except Exception as e:
            await message.reply(f'Error: {e}')
        log('Admin used /log command')
    else:
        log(f'{message.from_user.full_name}({message.from_user.id}) try use /log command')
        await message.reply('You are not an admin')


@dp.message(StateFilter(FSM.processing))
async def processing_message_handler(message: Message, state: FSMContext) -> None:
    await message.reply('The request is being processed. Please wait. If it\'s stuck, write to the [admin](@gvb3a)')


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

        text = str(message.caption) if message.caption else 'Describe the document or answer a prevate question'

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
     
    for file in input_files:  # If the file is not a picture, convert the file to text and add it to the user message
        if not(file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.webp')):
            messages[-1]['content'] += f'\n\n{file}:\n{files_to_text(file)}'
            input_files.remove(file)

    log(f'new message by {user}. messages: {text}, files: {input_files}')


    # ======================= select tool =======================
    tools = llm_select_tool(messages=messages, files=input_files, provider='google')
    if tools == []:
        temp_message_text[0] = temp_message_text[0][:-2] + '✅'
    else:
        temp_message_text[0] = temp_message_text[0][:-2] + '(' +','.join(set([i['func_name'] for i in tools])) + ')✅'
    await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text='\n'.join(temp_message_text))


    # ======================= use tool =======================
    tool_result, output_files = await llm_use_tool(tools=tools)
    temp_message_text[1] = temp_message_text[1][:-2] + '✅'
    await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text='\n'.join(temp_message_text))
    
    
    # ======================= inceset to database =======================
    sql_insert_message(user_id=user_id, role='user', content=text)
    if bool(tool_result) + bool(output_files):
        messages.append({'role': 'system', 'content': 'tool result:\n' + tool_result})
        sql_insert_message(user_id=user_id, role='system', content='tool result:\n' + tool_result)
        
        
    # ======================= get answer and record this =======================
    answer = llm_api(messages=messages, files=input_files, provider='google')


    await bot.delete_message(chat_id=chat_id, message_id=temp_message_id)
    log(f'answer to {user}({text}): {answer}')
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
            print(e)
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
@dp.callback_query(F.data[:17] == 'translate_message')
async def callback_translate_message(callback: CallbackQuery):
    'translate_message-{message_hash}-{user_text_language}'
    message_hash = callback.data.split('-')[1]
    user_text_language = callback.data.split('-')[2]

    text = sql_get_message_by_hash(message_hash)
    translated = translate(text, user_text_language)

    
    log(f'translate_message - User: {callback.from_user.full_name}, message: {text}, translated: {translated}, message_hash: {message_hash}')
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
        log(f'User: {callback.from_user.full_name}, message: {text}', error=True)
        await callback.answer()
        return
    
    str_result, image = code_interpreter(code)

    if str_result.replace('\n', '') == '':
        str_result = 'no text output'
    
    if image:
        await bot.send_photo(chat_id=callback.from_user.id, photo=FSInputFile(image))
        os.remove(image)

    
    log(f'User: {callback.from_user.full_name}, result: {str_result}, image: {bool(image)}, message_hash: {message_hash}, code: {code}')
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
        log(f'User: {callback.from_user.full_name}, latex: {latex}, message_hash: {message_hash}')
    else:
        log(f'User: {callback.from_user.full_name}, latex: {latex}, message_hash: {message_hash}', error=True)
        await callback.message.answer('Error in latex rendering')
    sql_insert_message(user_id=callback.from_user.id, role='system', content=f'latex rendering result: {bool(file_name)}')
    await callback.answer()
    

@dp.callback_query(F.data[:22] == 'translate_help_message')
async def callback_render_latex(callback: CallbackQuery):
    language = callback.data.split('-')[1]
    translated = translate(text=help_message, target_language=language, source_language='en')

    log(f'User: {callback.from_user.full_name}, language: {language}')

    try:
        await callback.message.answer(translated, parse_mode='Markdown')
    except:
        await callback.message.answer(translated)

    await callback.answer()



if __name__ == '__main__':
    log('Bot is launched')
    dp.run_polling(bot)
