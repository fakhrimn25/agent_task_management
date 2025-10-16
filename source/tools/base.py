import aiohttp
from typing import *
from loguru import logger
from pydantic import BaseModel

class BaseTaskManagement(BaseModel):
    """
    """

    async def _requests(self, uri: str, params: dict, service_name: str, method: Literal['post', 'get', 'put'] = 'post', timeout: int = 10, **kwargs) -> dict:
        logger.info(f'AIOHTTP requests to {service_name.upper()}')
        timeout = aiohttp.ClientTimeout(total=timeout)

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:

                if method == 'post':
                    payload = {'url': uri, 'json': params, **kwargs}
                    func = session.post
                elif method == 'put':
                    payload = {'url': uri, 'json': params, **kwargs}
                    func = session.put
                else:
                    payload = {'url': uri, 'params': params, **kwargs}
                    func = session.get

                async with func(**payload) as response:
                    if response.status < 300:
                        logger.info(f'AIOHTTP success requests to {service_name.upper()}')
                        result = await response.json()
                        return result
                    else:
                        detail = await response.json()
                        raise ConnectionError(f'Error {service_name.upper()} status code {response.status}. Detail: {detail.get("detail", detail)}')
        except aiohttp.ClientError as e:
            logger.error(f'ClientError when calling {service_name.upper()}: {str(e)}')
            raise
        except Exception as e:
            logger.error(f'Unexpected error in _requests to {service_name.upper()}: {str(e)}')
            raise