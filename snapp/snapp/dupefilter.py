from scrapy.dupefilters import BaseDupeFilter

class NoDupeFilter(BaseDupeFilter):

    def request_seen(self, request):
        return False  # False means it's not a duplicate

    def clear(self):
        # This method does nothing for now, but you can add cleanup code if necessary.
        pass

    @classmethod
    def from_settings(cls, settings):
        return cls()

    @classmethod
    def from_spider(cls, spider):
        return cls()
