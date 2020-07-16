import time
from datetime import timedelta
from typing import List

from django.core.files.base import ContentFile
from django.db import connection
from django.utils.timezone import now

from core.models import Image
from core.mp_scrapers.wildberries.wildberries_base import WildberriesBaseScraper
from core.types import RequestBody


class WildberriesImageScraper(WildberriesBaseScraper):
    def update_from_mp(self) -> None:
        start = time.time()
        connection.close()
        images = self._get_images_to_download()
        self._download_images_and_update_fields(images)
        print(f'Done in {time.time() - start:0.0f} seconds')

    def _get_images_to_download(self) -> List[Image]:
        current_time = now()
        # Choose timedelta properly!!!
        frozen_start_time = current_time + timedelta(minutes=10)
        filtered_images = Image.objects.select_for_update(skip_locked=True).filter(
            mp_source=self.mp_source, next_parse_time__lte=current_time,
            start_parse_time__gte=frozen_start_time).order_by('next_parse_time')[:self.config.bulk_item_step]
        for image in filtered_images:
            image.start_parse_time = current_time
        Image.objects.bulk_update(filtered_images, ['start_parse_time'])
        return filtered_images

    def _download_images_and_update_fields(self, images: List[Image]) -> None:
        for image in images:
            img_bytes, _, status_code = self.connector.get_page(RequestBody(image.mp_link, 'get', parsing_type='image'))
            if status_code == 200:
                image.image_file.save(image.mp_link.split('/')[-1], ContentFile(img_bytes), save=False)
            else:
                print(f'Can not find image on link {image.mp_link}')
            image.next_parse_time = now() + image.parse_frequency
            image.start_parse_time = None
        Image.objects.bulk_update(images, ['image_file', 'next_parse_time', 'start_parse_time'])
