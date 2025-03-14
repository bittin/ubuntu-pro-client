import textwrap

import mock
import pytest

from uaclient.cli.formatter import Block, ContentAlignment
from uaclient.cli.formatter import ProOutputFormatterConfig as POFC
from uaclient.cli.formatter import Table, create_link, real_len, wrap_text

M_PATH = "uaclient.cli.formatter."


class TestProFormatterConfig:
    @pytest.mark.parametrize(
        "system_encoding,expected_use_utf8",
        ((None, False), ("iso-8859-13", False), ("utf-8", True)),
    )
    def test_use_utf8(self, system_encoding, expected_use_utf8, FakeConfig):
        cfg = FakeConfig()

        with mock.patch(M_PATH + "sys.stdout") as m_stdout:
            m_stdout.encoding = system_encoding
            POFC.init(cfg)

        assert POFC.use_utf8 is expected_use_utf8

    @pytest.mark.parametrize("is_tty", (True, False))
    @pytest.mark.parametrize("env_no_color", ("True", None))
    @mock.patch(M_PATH + "sys.stdout.isatty")
    @mock.patch(M_PATH + "os.getenv")
    def test_color_config(
        self,
        m_getenv,
        m_is_tty,
        is_tty,
        env_no_color,
        FakeConfig,
    ):
        cfg = FakeConfig()

        m_is_tty.return_value = is_tty

        m_getenv.return_value = env_no_color

        POFC.init(cfg)

        expected_result = True
        if any((not is_tty, env_no_color)):
            expected_result = False

        assert POFC.use_color is expected_result

        POFC.disable_color()
        assert POFC.use_color is False


class TestCreateLink:
    def test_creates_link(self):
        assert (
            "\x1b]8;;http://example.test\x1b\\some link\x1b]8;;\x1b\\"
            == create_link(text="some link", url="http://example.test")
        )


class TestRealLen:
    @pytest.mark.parametrize(
        "input_string,expected_length",
        (
            ("", 0),
            ("input text", 10),
            ("\033[1mbold text\033[0m", 9),
            ("\033[91mred text\033[0m", 8),
            ("\033[1m\033[91mbold and red text\033[0m", 17),
            ("some \033[1mbold\033[0m and some \033[91mred\033[0m text", 27),
        ),
    )
    def test_length_ignores_color(self, input_string, expected_length):
        assert expected_length == real_len(input_string)

    def test_length_ignores_links(self):
        str_with_link = (
            "There is an "
            "\x1b]8;;https://example.com\x1b\\example link here\x1b]8;;\x1b\\"
            " to be clicked"
        )
        assert 43 == real_len(str_with_link)


class TestWrapText:
    def test_single_line_wrapped(self):
        assert ["example"] == wrap_text("example", 20)

        long_string = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            "Pellentesque diam nulla, efficitur a orci non, "
            "scelerisque lobortis felis."
        )
        assert [
            "Lorem ipsum dolor sit amet,",
            "consectetur adipiscing elit.",
            "Pellentesque diam nulla,",
            "efficitur a orci non,",
            "scelerisque lobortis felis.",
        ] == wrap_text(long_string, 30)

        colored_string = (
            "some \033[1mbold\033[0m and include "
            "the \033[91mred\033[0m text too"
        )
        assert len(colored_string) == 55
        assert [colored_string] == wrap_text(colored_string, 40)
        assert [
            "some \x1b[1mbold\x1b[0m and",
            "include the \x1b[91mred\x1b[0m text",
            "too",
        ] == wrap_text(colored_string, 20)

        string_with_link = (
            "There is an "
            "\x1b]8;;https://example.com\x1b\\example link here\x1b]8;;\x1b\\"
            " to be clicked"
        )
        assert len(string_with_link) == 76
        assert [string_with_link] == wrap_text(string_with_link, 45)
        assert [
            "There is an \x1b]8;;https://example.com\x1b\\example",
            "link here\x1b]8;;\x1b\\ to be",
            "clicked",
        ] == wrap_text(string_with_link, 20)


class TestTable:
    @pytest.mark.parametrize(
        "input_str,input_len,expected_value",
        (
            ("", 0, ""),
            ("", 5, "     "),
            ("test", 2, "test"),
            ("test", 4, "test"),
            ("test", 10, "test      "),
        ),
    )
    def test_ljust(self, input_str, input_len, expected_value):
        assert expected_value == Table.ljust(input_str, input_len)

    @pytest.mark.parametrize(
        "input_str,input_len,expected_value",
        (
            ("", 0, ""),
            ("", 5, "     "),
            ("test", 2, "test"),
            ("test", 4, "test"),
            ("test", 10, "      test"),
        ),
    )
    def test_rjust(self, input_str, input_len, expected_value):
        assert expected_value == Table.rjust(input_str, input_len)

    @pytest.mark.parametrize(
        "headers,rows,alignment,expected_msg",
        (
            (None, None, None, "Empty table not supported."),
            (
                None,
                [["a", "b"], [], ["c", "d"]],
                None,
                "Empty row not supported.",
            ),
            (
                None,
                [["a", "b"], ["c", "d", "e"], ["f", "g"]],
                None,
                "Mixed lengths in table content.",
            ),
            (
                ["h1", "h2", "h3"],
                [["a", "b"], ["c", "d"], ["e", "f"]],
                None,
                "Mixed lengths in table content.",
            ),
            (
                ["h1", "h2"],
                [["a", "b"], ["c", "d"], ["e", "f"]],
                [ContentAlignment.RIGHT],
                "'alignment' list should have length 2",
            ),
        ),
    )
    def test_validate_rejects_invalid_entries(
        self, headers, rows, alignment, expected_msg
    ):
        with pytest.raises(ValueError) as error:
            Table(headers=headers, rows=rows, alignment=alignment)

        assert expected_msg in str(error.value)

    def test_column_sizes(self):
        table = Table(
            ["header1", "h2", "h3", "h4"],
            [
                ["a", "bc", "de", "f"],
                ["b", "de", "fg", "wow this is a really big string of data"],
                ["c", "fg", "hijkl", "m"],
            ],
        )
        assert table.column_sizes == [7, 2, 5, 39]

    def test_line_length(self):
        table = Table(
            ["header1", "h2", "h3", "h4"],
            [
                ["a", "bc", "de", "f"],
                ["b", "de", "fg", "wow this is a really big string of data"],
                ["c", "fg", "hijkl", "m"],
            ],
        )
        assert table._get_line_length() == 59

    @mock.patch(M_PATH + "sys.stdout.isatty", return_value=True)
    def test_wrap_last_column(self, _m_is_tty):
        table = Table(
            ["header1", "h2", "h3", "h4"],
            [
                ["a", "bc", "de", "f"],
                ["b", "de", "fg", "wow this is a really big string of data"],
                ["c", "fg", "hijkl", "m"],
            ],
        )
        assert table.wrap_last_column(max_length=40) == [
            table.rows[0],
            ["b", "de", "fg", "wow this is a"],
            [" ", " ", " ", "really big string of"],
            [" ", " ", " ", "data"],
            table.rows[2],
        ]

    @mock.patch(M_PATH + "sys.stdout.isatty", return_value=True)
    def test_to_string_wraps_to_length(self, _m_is_tty, FakeConfig):
        POFC.init(FakeConfig())
        table = Table(
            ["header1", "h2", "h3", "h4"],
            [
                ["a", "bc", "de", "f"],
                ["b", "de", "fg", "wow this is a really big string of data"],
                ["c", "fg", "hijkl", "m"],
            ],
        )
        assert table.to_string(line_length=40) == textwrap.dedent(
            """\
            \x1b[1mheader1  h2  h3     h4\x1b[0m
            a        bc  de     f
            b        de  fg     wow this is a
                                really big string of
                                data
            c        fg  hijkl  m
            """
        )

    @mock.patch(M_PATH + "sys.stdout.isatty", return_value=False)
    def test_columns_align_to_the_right(self, _m_is_tty, FakeConfig):
        POFC.init(FakeConfig())
        table = Table(
            ["header1", "h2", "h3", "h4"],
            [
                ["a", "bc", "de", "f"],
                ["b", "de", "fg", "wow this is a really big string of data"],
                ["c", "fg", "hijkl", "m"],
            ],
            alignment=[ContentAlignment.RIGHT] * 4,
        )
        assert table.to_string() == textwrap.dedent(
            """\
            header1  h2     h3                                       h4
                  a  bc     de                                        f
                  b  de     fg  wow this is a really big string of data
                  c  fg  hijkl                                        m
            """  # noqa: E501
        )
        assert table.to_string(line_length=40) == textwrap.dedent(
            """\
            header1  h2     h3                    h4
                  a  bc     de                     f
                  b  de     fg         wow this is a
                                really big string of
                                                data
                  c  fg  hijkl                     m
            """
        )

    @mock.patch(M_PATH + "sys.stdout.isatty", return_value=True)
    @mock.patch(
        M_PATH + "os.get_terminal_size",
        return_value=mock.MagicMock(columns=40),
    )
    def test_to_string_wraps_to_terminal_size(
        self, _m_terminal_size, _m_is_tty, FakeConfig
    ):
        POFC.init(FakeConfig())
        table = Table(
            ["header1", "h2", "h3", "h4"],
            [
                [create_link(text="a", url="example.com"), "bc", "de", "f"],
                ["b", "de", "fg", "wow this is a really big string of data"],
                ["c", "fg", "hijkl", "m"],
            ],
        )
        assert table.to_string() == textwrap.dedent(
            """\
            \x1b[1mheader1  h2  h3     h4\x1b[0m
            \x1b]8;;example.com\x1b\\a\x1b]8;;\x1b\\        bc  de     f
            b        de  fg     wow this is a
                                really big string of
                                data
            c        fg  hijkl  m
            """
        )

    @mock.patch(M_PATH + "sys.stdout.isatty", return_value=False)
    # There is no terminal size if you are not in a tty
    @mock.patch(
        M_PATH + "os.get_terminal_size",
        side_effect=OSError(),
    )
    def test_to_string_no_wrap_if_no_tty(
        self, _m_terminal_size, _m_is_tty, FakeConfig
    ):
        POFC.init(FakeConfig())
        table = Table(
            ["header1", "h2", "h3", "h4"],
            [
                [create_link(text="a", url="example.com"), "bc", "de", "f"],
                [
                    "b",
                    "de",
                    "fg",
                    "wow this is a really big string of data" * 3,
                ],
                ["c", "fg", "hijkl", "m"],
            ],
        )
        assert table.to_string() == textwrap.dedent(
            """\
            header1  h2  h3     h4
            a        bc  de     f
            b        de  fg     wow this is a really big string of datawow this is a really big string of datawow this is a really big string of data
            c        fg  hijkl  m
            """  # noqa: E501
        )


class TestBlock:
    @mock.patch(M_PATH + "sys.stdout.isatty", return_value=False)
    @mock.patch(
        M_PATH + "os.get_terminal_size",
        side_effect=OSError(),
    )
    def test_indents_and_wraps_content_when_len_specified(
        self, _m_terminal_size, _m_is_tty, FakeConfig
    ):
        POFC.init(FakeConfig())
        block = Block(
            title="Example Title",
            content=[
                "Smaller content line",
                "A slightly bigger line which needs to be wrapped to fit the screen",  # noqa: E501
                Block(
                    title="Inner block",
                    content=[
                        "Another small content line",
                        "Another slightly bigger line which needs to be wrapped to fit the screen",  # noqa: E501
                    ],
                ),
                Table(
                    rows=[
                        [
                            "1",
                            "Table bigger last column which needs to be wrapped to fit the screen",  # noqa: E501
                        ],
                        [
                            "2",
                            "Table bigger last column which needs to be wrapped to fit the screen",  # noqa: E501
                        ],
                        [
                            "3",
                            "Table bigger last column which needs to be wrapped to fit the screen",  # noqa: E501
                        ],
                    ]
                ),
            ],
        )
        assert block.to_string() == textwrap.dedent(
            """\
            Example Title
                Smaller content line
                A slightly bigger line which needs to be wrapped to fit the screen
                Inner block
                    Another small content line
                    Another slightly bigger line which needs to be wrapped to fit the screen
                1  Table bigger last column which needs to be wrapped to fit the screen
                2  Table bigger last column which needs to be wrapped to fit the screen
                3  Table bigger last column which needs to be wrapped to fit the screen
            """  # noqa: E501
        )
        assert block.to_string(line_length=40) == textwrap.dedent(
            """\
            Example Title
                Smaller content line
                A slightly bigger line which needs
                to be wrapped to fit the screen
                Inner block
                    Another small content line
                    Another slightly bigger line
                    which needs to be wrapped to fit
                    the screen
                1  Table bigger last column which
                   needs to be wrapped to fit the
                   screen
                2  Table bigger last column which
                   needs to be wrapped to fit the
                   screen
                3  Table bigger last column which
                   needs to be wrapped to fit the
                   screen
            """
        )
