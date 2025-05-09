#
#
#

from json import load as json_load
from os.path import dirname, join
from unittest import TestCase
from unittest.mock import Mock, call
from urllib.parse import parse_qs

from requests import HTTPError
from requests_mock import ANY
from requests_mock import mock as requests_mock

from octodns.provider.yaml import YamlProvider
from octodns.record import Record
from octodns.zone import Zone

from octodns_ultra import UltraNoZonesExistException, UltraProvider


def _get_provider():
    '''
    Helper to return a provider after going through authentication sequence
    '''
    with requests_mock() as mock:
        mock.post(
            'https://restapi.ultradns.com/v2/authorization/token',
            status_code=200,
            text='{"token type": "Bearer", "refresh_token": "abc", '
            '"access_token":"123", "expires_in": "3600"}',
        )
        return UltraProvider(
            'test', 'testacct', 'user', 'pass', strict_supports=False
        )


class TestUltraProvider(TestCase):
    expected = Zone('unit.tests.', [])
    host = 'https://restapi.ultradns.com'
    empty_body = [{"errorCode": 70002, "errorMessage": "Data not found."}]

    expected = Zone('unit.tests.', [])
    source = YamlProvider('test', join(dirname(__file__), 'config'))
    source.populate(expected)

    def test_login(self):
        path = '/v2/authorization/token'

        # Bad Auth
        with requests_mock() as mock:
            mock.post(
                f'{self.host}{path}',
                status_code=401,
                text='{"errorCode": 60001}',
            )
            with self.assertRaises(Exception) as ctx:
                UltraProvider('test', 'account', 'user', 'wrongpass')
            self.assertEqual('Unauthorized', str(ctx.exception))

        # Good Auth
        with requests_mock() as mock:
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            mock.post(
                f'{self.host}{path}',
                status_code=200,
                request_headers=headers,
                text='{"token type": "Bearer", "refresh_token": "abc", '
                '"access_token":"123", "expires_in": "3600"}',
            )
            UltraProvider('test', 'account', 'user', 'rightpass')
            self.assertEqual(1, mock.call_count)
            expected_payload = (
                "grant_type=password&username=user&" "password=rightpass"
            )
            self.assertEqual(
                parse_qs(mock.last_request.text), parse_qs(expected_payload)
            )

    def test_get_zones(self):
        provider = _get_provider()
        path = "/v3/zones"

        # Test authorization issue
        with requests_mock() as mock:
            mock.get(
                f'{self.host}{path}',
                status_code=400,
                json={
                    "errorCode": 60004,
                    "errorMessage": "Authorization Header required",
                },
            )
            with self.assertRaises(HTTPError) as ctx:
                zones = provider.zones
            self.assertEqual(400, ctx.exception.response.status_code)

        # Test no zones exist error
        with requests_mock() as mock:
            mock.get(
                f'{self.host}{path}',
                status_code=404,
                headers={'Authorization': 'Bearer 123'},
                json=self.empty_body,
            )
            zones = provider.zones
            self.assertEqual(1, mock.call_count)
            self.assertEqual(list(), zones)

        # Reset zone cache so they are queried again
        provider._zones = None

        with requests_mock() as mock:
            payload = {
                "cursorInfo": {},
                "zones": [
                    {
                        "properties": {
                            "name": "testzone123.com.",
                            "accountName": "testaccount",
                            "type": "PRIMARY",
                            "dnssecStatus": "UNSIGNED",
                            "status": "ACTIVE",
                            "owner": "user",
                            "resourceRecordCount": 5,
                            "lastModifiedDateTime": "2020-06-19T00:47Z",
                        }
                    }
                ],
            }

            mock.get(
                f'{self.host}{path}',
                status_code=200,
                headers={'Authorization': 'Bearer 123'},
                json=payload,
            )
            zones = provider.zones
            self.assertEqual(1, mock.call_count)
            self.assertEqual(1, len(zones))
            self.assertEqual('testzone123.com.', zones[0])
            zones = provider.list_zones()
            self.assertEqual(1, mock.call_count)
            self.assertEqual(1, len(zones))
            self.assertEqual('testzone123.com.', zones[0])

        # Test different paging behavior
        provider._zones = None
        with requests_mock() as mock:
            mock.get(
                f'{self.host}{path}?limit=1000&q=zone_type%3APRIMARY',
                status_code=200,
                json={
                    "cursorInfo": {
                        "next": "em9uZS50ZXN0LjpORVhUCg==",
                        "last": "fjpMQVNU",
                    },
                    "zones": [],
                },
            )
            mock.get(
                f'{self.host}{path}?limit=1000&q=zone_type%3APRIMARY'
                '&cursor=em9uZS50ZXN0LjpORVhUCg==',
                status_code=200,
                json={
                    "cursorInfo": {
                        "first": "OkZJUlNU",
                        "previous": "OlBSRVZJT1VT",
                    },
                    "zones": [],
                },
            )
            zones = provider.zones
            self.assertEqual(2, mock.call_count)

    def test_request(self):
        provider = _get_provider()
        path = '/foo'
        payload = {'a': 1}

        with requests_mock() as mock:
            mock.get(
                f'{self.host}{path}',
                status_code=401,
                headers={'Authorization': 'Bearer 123'},
                json={},
            )
            with self.assertRaises(Exception) as ctx:
                provider._get(path)
            self.assertEqual('Unauthorized', str(ctx.exception))

        # Test all GET patterns
        with requests_mock() as mock:
            mock.get(
                f'{self.host}{path}',
                status_code=200,
                headers={'Authorization': 'Bearer 123'},
                json=payload,
            )
            provider._get(path, json=payload)

            mock.get(
                f'{self.host}{path}?a=1',
                status_code=200,
                headers={'Authorization': 'Bearer 123'},
            )
            provider._get(path, params=payload, json_response=False)

        # Test all POST patterns
        with requests_mock() as mock:
            mock.post(
                f'{self.host}{path}',
                status_code=200,
                headers={'Authorization': 'Bearer 123'},
                json=payload,
            )
            provider._post(path, json=payload)

            mock.post(
                f'{self.host}{path}',
                status_code=200,
                headers={'Authorization': 'Bearer 123'},
                text="{'a':1}",
            )
            provider._post(path, data=payload, json_response=False)

        # Test all PUT patterns
        with requests_mock() as mock:
            mock.put(
                f'{self.host}{path}',
                status_code=200,
                headers={'Authorization': 'Bearer 123'},
                json=payload,
            )
            provider._put(path, json=payload)

        # Test all DELETE patterns
        with requests_mock() as mock:
            mock.delete(
                f'{self.host}{path}',
                status_code=200,
                headers={'Authorization': 'Bearer 123'},
            )
            provider._delete(path, json_response=False)

    def test_zone_records(self):
        provider = _get_provider()
        zone_payload = {
            "cursorInfo": {},
            "zones": [{"properties": {"name": "octodns1.test."}}],
        }

        records_payload = {
            "zoneName": "octodns1.test.",
            "rrSets": [
                {
                    "ownerName": "octodns1.test.",
                    "rrtype": "NS (2)",
                    "ttl": 86400,
                    "rdata": ["ns1.octodns1.test."],
                },
                {
                    "ownerName": "octodns1.test.",
                    "rrtype": "SOA (6)",
                    "ttl": 86400,
                    "rdata": [
                        "pdns1.ultradns.com. phelps.netflix.com. 1 10 10 10 10"
                    ],
                },
            ],
            "resultInfo": {"totalCount": 2, "offset": 0, "returnedCount": 2},
        }

        zone_path = '/v3/zones'
        rec_path = '/v2/zones/octodns1.test./rrsets'
        with requests_mock() as mock:
            mock.get(
                f'{self.host}{zone_path}?limit=1000&q=zone_type%3APRIMARY',
                status_code=200,
                json=zone_payload,
            )
            mock.get(
                f'{self.host}{rec_path}?offset=0&limit=1000',
                status_code=200,
                json=records_payload,
            )

            zone = Zone('octodns1.test.', [])
            self.assertTrue(provider.zone_records(zone))
            self.assertEqual(mock.call_count, 2)

            # Populate the same zone again and confirm cache is hit
            self.assertTrue(provider.zone_records(zone))
            self.assertEqual(mock.call_count, 2)

    def test_populate(self):
        provider = _get_provider()

        # Non-existent zone doesn't populate anything
        with requests_mock() as mock:
            mock.get(ANY, status_code=404, json=self.empty_body)

            zone = Zone('unit.tests.', [])
            provider.populate(zone)
            self.assertEqual(set(), zone.records)

        # re-populating the same non-existent zone uses cache and makes no
        # calls
        again = Zone('unit.tests.', [])
        provider.populate(again)
        self.assertEqual(set(), again.records)

        # Test zones with data
        provider._zones = None
        path = '/v3/zones'
        with requests_mock() as mock:
            with open('tests/fixtures/ultra-zones-page-1.json') as fh:
                mock.get(
                    f'{self.host}{path}?limit=1000&q=zone_type%3APRIMARY',
                    status_code=200,
                    text=fh.read(),
                )
            with open('tests/fixtures/ultra-zones-page-2.json') as fh:
                mock.get(
                    f'{self.host}{path}?limit=1000&q=zone_type%3APRIMARY&'
                    'cursor=b2N0b2RuczE4LnRlc3QuOk5FWFQK',
                    status_code=200,
                    text=fh.read(),
                )
            with open('tests/fixtures/ultra-records-page-1.json') as fh:
                rec_path = '/v2/zones/octodns1.test./rrsets'
                mock.get(
                    f'{self.host}{rec_path}?offset=0&limit=1000',
                    status_code=200,
                    text=fh.read(),
                )
            with open('tests/fixtures/ultra-records-page-2.json') as fh:
                rec_path = '/v2/zones/octodns1.test./rrsets'
                mock.get(
                    f'{self.host}{rec_path}?offset=10&limit=1000',
                    status_code=200,
                    text=fh.read(),
                )

            zone = Zone('octodns1.test.', [])

            self.assertTrue(provider.populate(zone))
            self.assertEqual('octodns1.test.', zone.name)
            self.assertEqual(11, len(zone.records))
            self.assertEqual(4, mock.call_count)

    def test_apply(self):
        provider = _get_provider()

        provider._request = Mock()

        provider._request.side_effect = [
            UltraNoZonesExistException('No Zones'),
            None,  # zone create
        ] + [
            None
        ] * 16  # individual record creates

        # non-existent zone, create everything
        plan = provider.plan(self.expected)
        self.assertEqual(14, len(plan.changes))
        self.assertEqual(14, provider.apply(plan))
        self.assertFalse(plan.exists)

        provider._request.assert_has_calls(
            [
                # created the domain
                call(
                    'POST',
                    '/v2/zones',
                    json={
                        'properties': {
                            'name': 'unit.tests.',
                            'accountName': 'testacct',
                            'type': 'PRIMARY',
                        },
                        'primaryCreateInfo': {'createType': 'NEW'},
                    },
                ),
                # Validate multi-ip apex A record is correct
                call(
                    'POST',
                    '/v2/zones/unit.tests./rrsets/A/unit.tests.',
                    json={
                        'ttl': 300,
                        'rdata': ['1.2.3.4', '1.2.3.5'],
                        'profile': {
                            '@context': 'http://schemas.ultradns.com/RDPool.jsonschema',
                            'order': 'FIXED',
                            'description': 'unit.tests.',
                        },
                    },
                ),
                # make sure semicolons are not escaped when sending data
                call(
                    'POST',
                    '/v2/zones/unit.tests./rrsets/TXT/txt.unit.tests.',
                    json={
                        'ttl': 600,
                        'rdata': [
                            'Bah bah black sheep',
                            'have you any wool.',
                            'v=DKIM1;k=rsa;s=email;h=sha256;'
                            'p=A/kinda+of/long/string+with+numb3rs',
                        ],
                    },
                ),
                # make sure we updated NS records instead of trying to create them
                call(
                    'PUT',
                    '/v2/zones/unit.tests./rrsets/NS/unit.tests.',
                    json={'ttl': 3600, 'rdata': ['6.2.3.4.', '7.2.3.4.']},
                ),
            ],
            any_order=True,
        )
        # expected number of total calls
        self.assertEqual(16, provider._request.call_count)

        # Create sample rrset payload to attempt to alter
        with open('tests/fixtures/ultra-records-page-1.json') as fh:
            page1 = json_load(fh)
        with open('tests/fixtures/ultra-records-page-2.json') as fh:
            page2 = json_load(fh)
        mock_rrsets = list()
        mock_rrsets.extend(page1['rrSets'])
        mock_rrsets.extend(page2['rrSets'])

        # Seed a bunch of records into a zone and verify update / delete ops
        provider._request.reset_mock()
        provider._zones = ['octodns1.test.']
        provider.zone_records = Mock(return_value=mock_rrsets)

        provider._request.side_effect = [None] * 13

        wanted = Zone('octodns1.test.', [])
        wanted.add_record(
            Record.new(
                wanted,
                '',
                {
                    'ttl': 60,  # Change TTL
                    'type': 'A',
                    'value': '5.6.7.8',  # Change number of IPs (3 -> 1)
                },
            )
        )
        wanted.add_record(
            Record.new(
                wanted,
                'txt',
                {
                    'ttl': 3600,
                    'type': 'TXT',
                    'values': [  # Alter TXT value
                        "foobar",
                        "v=spf1 include:mail.server.net ?all",
                    ],
                },
            )
        )

        plan = provider.plan(wanted)
        self.assertEqual(10, len(plan.changes))
        self.assertEqual(10, provider.apply(plan))
        self.assertTrue(plan.exists)

        provider._request.assert_has_calls(
            [
                # Validate multi-ip apex A record replaced with standard A
                call(
                    'PUT',
                    '/v2/zones/octodns1.test./rrsets/A/octodns1.test.',
                    json={'ttl': 60, 'rdata': ['5.6.7.8']},
                ),
                # Make sure TXT value is properly updated
                call(
                    'PUT',
                    '/v2/zones/octodns1.test./rrsets/TXT/txt.octodns1.test.',
                    json={
                        'ttl': 3600,
                        'rdata': [
                            "foobar",
                            "v=spf1 include:mail.server.net ?all",
                        ],
                    },
                ),
                # Confirm a few of the DELETE operations properly occur
                call(
                    'DELETE',
                    '/v2/zones/octodns1.test./rrsets/A/a.octodns1.test.',
                    json_response=False,
                ),
                call(
                    'DELETE',
                    '/v2/zones/octodns1.test./rrsets/AAAA/aaaa.octodns1.test.',
                    json_response=False,
                ),
                call(
                    'DELETE',
                    '/v2/zones/octodns1.test./rrsets/CAA/caa.octodns1.test.',
                    json_response=False,
                ),
                call(
                    'DELETE',
                    '/v2/zones/octodns1.test./rrsets/CNAME/cname.octodns1.test.',
                    json_response=False,
                ),
            ],
            True,
        )

    def test_gen_data(self):
        provider = _get_provider()
        zone = Zone('unit.tests.', [])

        for name, _type, expected_path, expected_payload, expected_record in (
            # A
            (
                'a',
                'A',
                '/v2/zones/unit.tests./rrsets/A/a.unit.tests.',
                {'ttl': 60, 'rdata': ['1.2.3.4']},
                Record.new(
                    zone, 'a', {'ttl': 60, 'type': 'A', 'values': ['1.2.3.4']}
                ),
            ),
            (
                'a',
                'A',
                '/v2/zones/unit.tests./rrsets/A/a.unit.tests.',
                {
                    'ttl': 60,
                    'rdata': ['1.2.3.4', '5.6.7.8'],
                    'profile': {
                        '@context': 'http://schemas.ultradns.com/RDPool.jsonschema',
                        'order': 'FIXED',
                        'description': 'a.unit.tests.',
                    },
                },
                Record.new(
                    zone,
                    'a',
                    {'ttl': 60, 'type': 'A', 'values': ['1.2.3.4', '5.6.7.8']},
                ),
            ),
            # AAAA
            (
                'aaaa',
                'AAAA',
                '/v2/zones/unit.tests./rrsets/AAAA/aaaa.unit.tests.',
                {'ttl': 60, 'rdata': ['::1']},
                Record.new(
                    zone, 'aaaa', {'ttl': 60, 'type': 'AAAA', 'values': ['::1']}
                ),
            ),
            (
                'aaaa',
                'AAAA',
                '/v2/zones/unit.tests./rrsets/AAAA/aaaa.unit.tests.',
                {
                    'ttl': 60,
                    'rdata': ['::1', '::2'],
                    'profile': {
                        '@context': 'http://schemas.ultradns.com/RDPool.jsonschema',
                        'order': 'FIXED',
                        'description': 'aaaa.unit.tests.',
                    },
                },
                Record.new(
                    zone,
                    'aaaa',
                    {'ttl': 60, 'type': 'AAAA', 'values': ['::1', '::2']},
                ),
            ),
            # CAA
            (
                'caa',
                'CAA',
                '/v2/zones/unit.tests./rrsets/CAA/caa.unit.tests.',
                {'ttl': 60, 'rdata': ['0 issue foo.com']},
                Record.new(
                    zone,
                    'caa',
                    {
                        'ttl': 60,
                        'type': 'CAA',
                        'values': [
                            {'flags': 0, 'tag': 'issue', 'value': 'foo.com'}
                        ],
                    },
                ),
            ),
            # CNAME
            (
                'cname',
                'CNAME',
                '/v2/zones/unit.tests./rrsets/CNAME/cname.unit.tests.',
                {'ttl': 60, 'rdata': ['netflix.com.']},
                Record.new(
                    zone,
                    'cname',
                    {'ttl': 60, 'type': 'CNAME', 'value': 'netflix.com.'},
                ),
            ),
            # MX
            (
                'mx',
                'MX',
                '/v2/zones/unit.tests./rrsets/MX/mx.unit.tests.',
                {
                    'ttl': 60,
                    'rdata': ['1 mx1.unit.tests.', '1 mx2.unit.tests.'],
                },
                Record.new(
                    zone,
                    'mx',
                    {
                        'ttl': 60,
                        'type': 'MX',
                        'values': [
                            {'preference': 1, 'exchange': 'mx1.unit.tests.'},
                            {'preference': 1, 'exchange': 'mx2.unit.tests.'},
                        ],
                    },
                ),
            ),
            # NS
            (
                'ns',
                'NS',
                '/v2/zones/unit.tests./rrsets/NS/ns.unit.tests.',
                {'ttl': 60, 'rdata': ['ns1.unit.tests.', 'ns2.unit.tests.']},
                Record.new(
                    zone,
                    'ns',
                    {
                        'ttl': 60,
                        'type': 'NS',
                        'values': ['ns1.unit.tests.', 'ns2.unit.tests.'],
                    },
                ),
            ),
            # PTR
            (
                'ptr',
                'PTR',
                '/v2/zones/unit.tests./rrsets/PTR/ptr.unit.tests.',
                {'ttl': 60, 'rdata': ['a.unit.tests.']},
                Record.new(
                    zone,
                    'ptr',
                    {'ttl': 60, 'type': 'PTR', 'value': 'a.unit.tests.'},
                ),
            ),
            # SRV
            (
                '_srv._tcp',
                'SRV',
                '/v2/zones/unit.tests./rrsets/SRV/_srv._tcp.unit.tests.',
                {'ttl': 60, 'rdata': ['10 20 443 target.unit.tests.']},
                Record.new(
                    zone,
                    '_srv._tcp',
                    {
                        'ttl': 60,
                        'type': 'SRV',
                        'values': [
                            {
                                'priority': 10,
                                'weight': 20,
                                'port': 443,
                                'target': 'target.unit.tests.',
                            }
                        ],
                    },
                ),
            ),
            # TXT
            (
                'txt',
                'TXT',
                '/v2/zones/unit.tests./rrsets/TXT/txt.unit.tests.',
                {'ttl': 60, 'rdata': ['abc', 'def']},
                Record.new(
                    zone,
                    'txt',
                    {'ttl': 60, 'type': 'TXT', 'values': ['abc', 'def']},
                ),
            ),
            # ALIAS
            (
                '',
                'ALIAS',
                '/v2/zones/unit.tests./rrsets/APEXALIAS/unit.tests.',
                {'ttl': 60, 'rdata': ['target.unit.tests.']},
                Record.new(
                    zone,
                    '',
                    {'ttl': 60, 'type': 'ALIAS', 'value': 'target.unit.tests.'},
                ),
            ),
        ):
            # Validate path and payload based on record meet expectations
            path, payload = provider._gen_data(expected_record)
            self.assertEqual(expected_path, path)
            self.assertEqual(expected_payload, payload)

            # Use generator for record and confirm the output matches
            rec = provider._record_for(
                zone, name, _type, expected_payload, False
            )
            path, payload = provider._gen_data(rec)
            self.assertEqual(expected_path, path)
            self.assertEqual(expected_payload, payload)
