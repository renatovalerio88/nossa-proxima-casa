import unittest

from scripts.collect_public_pages import extract_real_photos


class CollectorPhotoTests(unittest.TestCase):
    def test_extracts_explicit_social_and_json_ld_photos(self):
        body = '''
        <html><head>
          <meta property="og:image" content="https://cdn.example.com/imovel/frente.jpg">
          <meta name="twitter:image" content="/fotos/sala.webp">
          <script type="application/ld+json">
          {"@type":"House","image":["https://cdn.example.com/imovel/quintal.jpeg","https://cdn.example.com/logo.png"]}
          </script>
        </head></html>
        '''
        photos = extract_real_photos(body, "https://www.example.com/anuncio/123")
        self.assertEqual(
            photos,
            [
                "https://cdn.example.com/imovel/frente.jpg",
                "https://www.example.com/fotos/sala.webp",
                "https://cdn.example.com/imovel/quintal.jpeg",
            ],
        )

    def test_rejects_generic_non_https_and_non_image_assets(self):
        body = '''
        <meta property="og:image" content="https://cdn.example.com/assets/placeholder.jpg">
        <meta property="og:image:url" content="http://cdn.example.com/imovel/frente.jpg">
        <meta name="twitter:image" content="https://cdn.example.com/imovel/arquivo.svg">
        '''
        self.assertEqual(extract_real_photos(body, "https://www.example.com/anuncio/123"), [])

    def test_deduplicates_and_limits_gallery(self):
        body = '''
        <meta property="og:image" content="https://cdn.example.com/a.jpg">
        <script type="application/ld+json">
        {"image":["https://cdn.example.com/a.jpg","https://cdn.example.com/b.jpg","https://cdn.example.com/c.jpg"]}
        </script>
        '''
        self.assertEqual(
            extract_real_photos(body, "https://www.example.com/anuncio/123", limit=2),
            ["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"],
        )

    def test_does_not_scan_arbitrary_img_tags(self):
        body = '<img src="https://cdn.example.com/card.jpg"><img src="https://cdn.example.com/banner.jpg">'
        self.assertEqual(extract_real_photos(body, "https://www.example.com/anuncio/123"), [])


if __name__ == "__main__":
    unittest.main()
