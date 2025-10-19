# https://e2b.dev/
import base64
from e2b_code_interpreter import Sandbox
from ...config.logger import logger


def code_interpreter(code: str) -> tuple[str, str | None]:
    '''Interprets and executes the given code in a sandboxed environment (https://e2b.dev/)'''
    with Sandbox() as sandbox:
        execution = sandbox.run_code(code)

        stdout = execution.logs.stdout
        stderr = execution.logs.stderr

        try:
            first_result = execution.results[0]
            if first_result.png:
                image_file_name = 'e2b_image.png'
                with open(image_file_name, 'wb') as f:
                    f.write(base64.b64decode(first_result.png))
            else:
                image_file_name = None
        except:
            image_file_name = None

        try:
            result = stdout[0]
        except:
            result = ''

        try:
            result += '\n' + stderr[0]
        except:
            pass
        
        logger.info(f'{result}, {image_file_name}')
        return result, image_file_name
