import time
from typing import List, Generator

from django.core.files.base import ContentFile
from django.db.models import QuerySet
from django.utils.timezone import now

from core.mp_scrapers.configs import WILDBERRIES_CONFIG
from core.utils.connector import Connector
from core.types import RequestBody
from core.models import Image
from core.mp_scrapers.wildberries.wildberries_base import get_mp_wb


class WildberriesImageScraper:
    def __init__(self):
        self.config = WILDBERRIES_CONFIG
        self.connector = Connector(use_proxy=self.config.use_proxy)
        self.mp_source = get_mp_wb()

        # Mock property. TODO: write full function for logging and loading update_start_time
        self.update_start_time = now()

    def update_from_mp(self) -> None:
        images_gen = self._get_images_to_download()

        counter = 1
        start = time.time()
        for images in images_gen:
            self._download_images_and_update_fields(images)

            print(f'Done step {counter} in {time.time() - start:0.0f} seconds')
            counter += 1
            start = time.time()

    def _get_images_to_download(self) -> Generator[List[Image], None, None]:
        image_no_pics = Image.objects.filter(mp_source=self.mp_source, image_file__isnull=True)
        yield from self._chunk_images_iterator(image_no_pics)

        not_updated_images = Image.objects.filter(mp_source=self.mp_source, modified_at__lte=self.update_start_time)
        yield from self._chunk_images_iterator(not_updated_images)

    def _chunk_images_iterator(self, filtered_images: QuerySet) -> Generator[List[Image], None, None]:
        chunked_images = []
        for filtered_item in filtered_images.iterator():
            if len(chunked_images) < self.config.bulk_item_step:
                chunked_images.append(filtered_item)
            else:
                yield chunked_images
                chunked_images.clear()

    def _download_images_and_update_fields(self, images: List[Image]) -> None:
        for image in images:
            img_bytes, _, status_code = self.connector.get_page(RequestBody(image.mp_link, 'get', parsing_type='image'))
            if status_code == 200:
                image.image_file.save(image.mp_link.split('/')[-1], ContentFile(img_bytes), save=False)
            else:
                print(f'Cann not find image on link {image.mp_link}')
        Image.objects.bulk_update(images, ['image_file'])
