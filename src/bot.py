from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
import os
from dotenv import load_dotenv
from datetime import datetime
import re


if __name__ == '__main__' or '.' not in __name__:
    from api import speech_recognition, llm_api, files_to_text, code_interpreter
    from llm_answer import system_prompt, llm_select_tool, llm_use_tool
    from sql import sql_check_user, sql_select_history, sql_insert_message
    from log import log
    from magic import markdown_to_html
else:
    from .api import speech_recognition, llm_api, files_to_text, code_interpreter
    from .llm_answer import system_prompt, llm_select_tool, llm_use_tool
    from .sql import sql_check_user, sql_select_history, sql_insert_message
    from .log import log
    from .magic import markdown_to_html
    

load_dotenv()

bot_token = os.getenv('BOT_TOKEN')


class FSM(StatesGroup):
    processing = State()  # is enabled if the request is being processed


bot = Bot(token=str(bot_token))
dp = Dispatcher()


async def download_file_for_id(file_id, extension):

    file = await bot.get_file(file_id)
    file_path = str(file.file_path)
    now = datetime.now()
    file_name = f'{now.strftime("%Y%m%d_%H%M%S")}.{extension}'

    await bot.download_file(file_path, file_name)

    return file_name


@dp.message(CommandStart())  # /start command handler
async def start_command_handler(message: Message) -> None:
    await message.answer('Hi! I am an AI agent that can search for information on the internet, use a calculator for large calculations and equations, summarize youtube videos, search for pictures, and execute code. How can I help you today?  \n\n[GitHub](https://github.com/Gvb3a/assistant)', parse_mode='Markdown')
    log(f'{message.from_user.full_name}({message.from_user.username})')


@dp.message(StateFilter(default_state))
async def message_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(FSM.processing)
    chat_id = message.chat.id
    user = message.from_user.full_name
    user_id =  message.from_user.id
    username = message.from_user.username
    message_id = message.message_id
    sql_check_user(user_id=user_id, telegram_name=user, telegram_username=username)

    temp_message_text = ['Selecting tool - 🔍', 'Using the tool - ⚙️', 'Generating response - 🤖']
    temp_message_id = message_id + 1

    input_files = []
    
    if message.voice:
        await message.reply('Recognizing audio...')
        file_name = await download_file_for_id(file_id=message.voice.file_id, extension='mp3')
        
        text = speech_recognition(file_name=file_name).strip()
        os.remove(file_name)
        
        temp_message_text[0] = temp_message_text[0][:-2] + '✅'
        await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text=f'Recognized: {text}')

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

        text = str(message.caption) if message.caption else 'Describe the document'

        temp_message_id += 1

    if message.text:
        text = str(message.text)
    
    await message.reply('\n'.join(temp_message_text))


    messages = sql_select_history(id=user_id)
    messages.insert(0, {'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': text})
    
    
    # If the file is not a picture, convert the file to text and add it to the user message
    for file in input_files:
        if not(file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.webp')):
            messages[-1]['content'] += f'\n\n{file}:\n{files_to_text(file)}'
            input_files.remove(file)

    log(f'new message by {user}. messages: {text}, files: {input_files}')

    tools = llm_select_tool(messages=messages, files=input_files, provider='google')
    temp_message_text[0] = temp_message_text[0][:-2] + '✅'
    await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text='\n'.join(temp_message_text))

    tool_result, output_files = await llm_use_tool(tools=tools)
    temp_message_text[1] = temp_message_text[1][:-2] + '✅'
    await bot.edit_message_text(chat_id=chat_id, message_id=temp_message_id, text='\n'.join(temp_message_text))

    
    sql_insert_message(user_id=user_id, role='user', content=text)

    if bool(tool_result) + bool(output_files):
        messages.append({'role': 'system', 'content': 'tool result:\n' + tool_result})
        sql_insert_message(user_id=user_id, role='system', content='tool result:\n' + tool_result)
        
    answer = llm_api(messages=messages, files=input_files, provider='google')
    await bot.delete_message(chat_id=chat_id, message_id=temp_message_id)
    log(f'answer to {user}({text}): {answer}')
    sql_insert_message(user_id=user_id, role='assistant', content=answer)


    # TODO: images don't send
    output_files = output_files[:9]
    if output_files:
        media_group = []

        for file in output_files:

            if file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.webp'):
                media = FSInputFile(file)
                media_group.append(InputMediaPhoto(media=media))
            else:
                document = FSInputFile(file)
                await bot.send_document(chat_id=chat_id, document=document)

        try:
            await message.answer_media_group(media=media_group)
        except Exception as e:
            print('media group error', e)


    if '```python' in answer:
        inline_button = InlineKeyboardButton(text='Run code ➡', callback_data='run_last_code')
        inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[[inline_button]])
    else:
        inline_keyboard = None

    while answer:
        try:
            await message.answer(markdown_to_html(answer[:4000]), parse_mode='HTML', reply_markup=inline_keyboard)
            inline_keyboard = None
        except Exception as e:
            print(e)
            await message.answer(answer[:4000])
        answer = answer[4000:]

    try:
        for file in output_files:
            if not file.startswith('https:'):
                try:
                    os.remove(file)
                except:
                    os.remove(file.split('/')[-1])  

    except Exception as e:
        print(e)

    await state.clear()


@dp.callback_query(F.data == 'run_last_code')
async def callback_run_last_code(callback: CallbackQuery):
    text = callback.message.md_text

    try:
        code = text.split('```python')[1].split('```')[0]
        code = re.sub(r'\\([_*()[\]{}#+\-!.<>|=`\\])', r'\1', code)
    except:
        code = None

    if not code:
        await bot.send_message(chat_id=callback.from_user.id, text='No code found')
        log(f'User: {callback.from_user.full_name}, message: {text}', error=True)
        await callback.answer()
        return
    print(code)
    str_result, image = code_interpreter(code)

    if str_result.replace('\n', '') == '':
        str_result = 'no text output'
    
    if image:
        await bot.send_photo(chat_id=callback.from_user.id, photo=FSInputFile(image))
        os.remove(image)

    
    log(f'User: {callback.from_user.full_name}, result: {str_result}, image: {bool(image)}, code: {code}')
    sql_insert_message(user_id=callback.from_user.id, role='system', content=f'The result of code execution that is visible to the user: {str_result}. \nif there\'s an image: {bool(image)}')

    while str_result:
        await bot.send_message(chat_id=callback.from_user.id, text=f'```output\n{str_result[:4000]}\n```', parse_mode='Markdown')
        str_result = str_result[4000:]
    
    callback.answer()
    
    


if __name__ == '__main__':
    log('Bot is launched')
    dp.run_polling(bot)
