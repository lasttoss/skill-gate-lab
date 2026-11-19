import unittest

from gate import frontmatter


class ParseTest(unittest.TestCase):
    def test_flat_keys_and_inline_list(self):
        doc = frontmatter.parse("---\nname: a\ndescription: hello there\ntags: [x, y]\n---\nbody\n", "t")
        self.assertEqual(doc.name, "a")
        self.assertEqual(doc.tags, ["x", "y"])
        self.assertEqual(doc.body, "body\n")

    def test_quoted_value_keeps_inner_colon(self):
        doc = frontmatter.parse('---\nname: a\ndescription: "one: two"\n---\nx\n', "t")
        self.assertEqual(doc.description, "one: two")

    def test_missing_block_raises(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.parse("no frontmatter here\n", "t")

    def test_unclosed_block_raises(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.parse("---\nname: a\n", "t")

    def test_bad_key_raises(self):
        with self.assertRaises(frontmatter.FrontmatterError):
            frontmatter.parse("---\nbad key: v\n---\nx\n", "t")

    def test_line_count(self):
        doc = frontmatter.parse("---\nname: a\n---\n1\n2\n3\n", "t")
        self.assertEqual(doc.lines, 7)


if __name__ == "__main__":
    unittest.main()
