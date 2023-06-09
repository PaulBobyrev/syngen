import pytest
import pandas as pd

from syngen.ml.vae.models.features import DateFeature

from tests.conftest import SUCCESSFUL_MESSAGE

test_data = [
            ({"Date": ["01-01-2020", "02/02/2000", "05-05-2020"]}, "%m-%d-%Y"),
            ({"Date": ["31-01-2020", "20/02/2000", "25-05-2020"]}, "%d-%m-%Y"),
            ({"Date": ["03/03/2000", "01/01/2020", "05-05-2020"]}, "%m/%d/%Y"),
            ({"Date": ["31/01/2020", "20/02/2000", "25/05/2020"]}, "%d/%m/%Y"),
            ({"Date": ["2020/01/01", "1999/01/09", "05-05-2020"]}, "%Y/%m/%d"),
            ({"Date": ["2020-01-01", "1999-01-09", "05-05-2020"]}, "%Y-%m-%d"),
            ({"Date": ["March 10, 2022", "September 11, 1900", "May 15, 1877"]}, "%B %d, %Y"),
            ({"Date": ["Jul 10, 2022", "Jan 11, 1900", "Feb 15, 1877"]}, "%b %d, %Y"),
            ({"Date": ["10 June 2022", "11 January 1900", "01 February 1877"]}, "%d %B %Y"),
            ({"Date": ["Jul 10 2022", "Jan 11 1900", "Feb 15 1877"]}, "%b %d %Y"),
            ({"Date": [
                "1989-01-01 00:00:00.000000",
                "1897-01-01 03:03:00.000000",
                "2020-01-01 03:03:03.000000"]}, "%Y-%m-%d"),
            ({"Date": [
                "1989/01/01 00:00:00.000000",
                "1897/01/01 03:03:00.000000",
                "2020/01/01 03:03:03.000000"]}, "%Y/%m/%d"),
            ({"Date": [
                "2010-10-23 18:25:00 BRST",
                "2012-01-19 17:21:00 BRST",
                "2002-05-09 11:31:00 BRST"]}, "%Y-%m-%d"),
            ({"Date": [
                "2010-10-23 18:25:00 +0300",
                "2012-01-19 17:21:00 +0300",
                "2002-05-09 11:31:00 +0300"]}, "%Y-%m-%d"),
            ({"Date": [
                "2012/01/19 17:21:00",
                "2012/01/19 17:21:00",
                "2012/01/19 17:21:00"]}, "%Y/%m/%d"),
            ({"Date": [
                "01/01/19 17:21:00",
                "02/02/00 15:01:10",
                "12/10/19 17:21:00"]}, "%d-%m-%Y"),
            ({"Date": [
                "01-01-19 17:21:00",
                "02-02-00 15:01:10",
                "12-10-19 17:21:00"]}, "%d-%m-%Y"),
            ({"Date": [
                "01-01-19 17:21:00",
                "02-02-00 15:01:10",
                "31/10/2019 17:21:00"]}, "%d/%m/%Y"),
            ({"Date": [
                "01/01/19 17:21:00",
                "02/02/00 15:01:10",
                "31-10-2019 17:21:00"]}, "%d-%m-%Y"),
            ({"Date": [
                "2021-07-07T15:16:01.795Z",
                "2022-07-07T15:16:01.795Z'",
                "2023-07-07T15:16:01.795Z'"]}, "%Y-%m-%d"),
        ]
@pytest.mark.parametrize("data, expected_date_format", test_data)
def test_validate_date_format(data, expected_date_format, rp_logger):
    rp_logger.info("Validating date format with data: %s and expected date format: %s", data, expected_date_format)
    data = pd.DataFrame(data)
    date_feature = DateFeature(name="date_feature")
    date_feature.fit(data)
    assert date_feature.date_format == expected_date_format
    rp_logger.info(SUCCESSFUL_MESSAGE)
