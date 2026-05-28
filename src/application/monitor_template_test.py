import re
from src.application.monitor_template import make_monitor_name, render_monitor


def test_make_monitor_name_with_ean():
    assert make_monitor_name(ean="4548736134034", title="Sony WH-1000XM5") == "ftp_4548736134034"


def test_make_monitor_name_without_ean():
    name = make_monitor_name(ean=None, title="Sony WH-1000XM5 Wireless")
    assert name.startswith("ftp_")
    assert re.match(r"^ftp_[a-z0-9_]+$", name)
    assert len(name) <= 44  # "ftp_" + 40 chars


def test_make_monitor_name_special_chars():
    name = make_monitor_name(ean=None, title="Product! With @Special #Chars")
    assert re.match(r"^ftp_[a-z0-9_]+$", name)


def test_render_monitor_contains_product_name():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=["telegram"],
    )
    assert "_PRODUCT_NAME = 'Sony WH-1000XM5'" in src or '_PRODUCT_NAME = "Sony WH-1000XM5"' in src


def test_render_monitor_contains_ean():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=["telegram"],
    )
    assert "_EAN = '4548736134034'" in src or '_EAN = "4548736134034"' in src


def test_render_monitor_uses_ean_as_query_when_available():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=["telegram"],
    )
    assert "_QUERY = '4548736134034'" in src or '_QUERY = "4548736134034"' in src


def test_render_monitor_uses_title_as_query_when_no_ean():
    src = render_monitor(
        name="ftp_sony_wh",
        product_name="Sony WH-1000XM5",
        ean=None,
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=[],
    )
    assert "_QUERY = 'Sony WH-1000XM5'" in src or '_QUERY = "Sony WH-1000XM5"' in src


def test_render_monitor_contains_schedule():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 0 * * *",
        notify_channels=[],
    )
    assert "0 0 * * *" in src


def test_render_monitor_contains_monitor_name():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=[],
    )
    assert "ftp_4548736134034" in src


def test_render_monitor_is_valid_python():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=["telegram"],
    )
    compile(src, "<monitor>", "exec")  # raises SyntaxError if invalid


def test_render_monitor_logs_price():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=[],
    )
    assert "ctx.logger.info" in src
    assert "_PRODUCT_NAME" in src


def test_render_monitor_formats_price_as_euros():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=[],
    )
    assert 'replace(".", ",")' in src
    assert "price_str" in src


def test_render_monitor_contains_findthatproduct_tag():
    src = render_monitor(
        name="ftp_4548736134034",
        product_name="Sony WH-1000XM5",
        ean="4548736134034",
        currency="EUR",
        schedule="0 */6 * * *",
        notify_channels=[],
    )
    assert 'tags=["findthatproduct"]' in src
