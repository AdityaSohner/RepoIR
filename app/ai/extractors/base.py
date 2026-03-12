class BaseExtractor:
    def extract(self, source) -> dict:
        """
        MUST return:
        {
            "raw_text": str,     # merged meaningful text
            "metadata": dict
        }
        """
        raise NotImplementedError
