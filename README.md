## UltraDNS provider for octoDNS

An [octoDNS](https://github.com/octodns/octodns/) provider that targets [UltraDNS](https://vercara.com/authoritative-dns).

### Installation

#### Command line

```
pip install octodns-ultra
```

#### requirements.txt/setup.py

Pinning specific versions or SHAs is recommended to avoid unplanned upgrades.

##### Versions

```
# Start with the latest versions and don't just copy what's here
octodns==0.21.1
octodns-ultra==1.2.0
```

##### SHAs

```
# Start with the latest/specific versions and don't just copy what's here
-e git+https://git@github.com/octodns/octodns.git@9da19749e28f68407a1c246dfdf65663cdc1c422#egg=octodns
-e git+https://git@github.com/octodns/octodns-ultra.git@ec9661f8b335241ae4746eea467a8509205e6a30#egg=octodns_ultra
```

### Configuration

```yaml
providers:
  ultra:
    class: octodns_ultra.UltraProvider
    # Ultra Account Name (required)
    account: env/ULTRA_ACCOUNT
    # Ultra username (required)
    username: env/ULTRA_USERNAME
    # Ultra password (required)
    password: env/ULTRA_PASSWORD
    # Valimail enabled on created zones (optional, default=False)
    # valimail: true
    # Enable UltraDNS managed DNSSEC (optional, default=False)
    # dnssec: true
```

### Support Information

#### API Version

Targets the UltraDNS REST API. [Documentation can be found here](https://docs.ultradns.com/Content/REST%20API/Content/REST%20API/What's%20New.htm).

#### Records

UltraProvider supports A, AAAA, CAA, CNAME, MX, NS, PTR, SPF, SRV, and TXT

#### Root NS Records

UltraProvider supports full root NS record management.

#### Dynamic

UltraProvider does not support dynamic records.

#### Provider Specific Meta

##### Valimail Monitor

Valimail monitor is an UltraDNS feature that automates the creation of email related DNS records. If enabled, octoDNS will ignore the records that the feature automatically adds to the domain.

More information on Valimail Monitor can be found in the [UltraDNS documentation](https://docs.ultradns.com/Content/REST%20API/Content/REST%20API/Valimail%20Monitor.htm).

##### DNSSEC

DNSSEC in UltraDNS is a zone level toggle. Enabling it will create UltraDNS managed DNSSEC related records such as KSK, ZSK, DNSKEY and DS.

More information on UltraDNS's DNSSEC implementation can be found in the [UltraDNS documentation](https://docs.ultradns.com/Content/REST%20API/Content/REST%20API/Zone%20DNSSEC%20APIs.htm).

To have some zones DNSSEC enabled and others not, the recommended implementation is to have two seperate providers configured, eg:


```yaml
providers:
  ultra:
    class: octodns_ultra.UltraProvider
    account: env/ULTRA_ACCOUNT
    username: env/ULTRA_USERNAME
    password: env/ULTRA_PASSWORD
    dnssec: true
  ultra_dnssec:
    class: octodns_ultra.UltraProvider
    account: env/ULTRA_ACCOUNT
    username: env/ULTRA_USERNAME
    password: env/ULTRA_PASSWORD
    dnssec: true

zones:
  dnssec-zone.net.:
    sources:
      - config
    targets:
      - ultra_dnssec

  no-dnssec-zone.net.:
    sources:
      - config
    targets:
      - ultra
```

### Development

See the [/script/](/script/) directory for some tools to help with the development process. They generally follow the [Script to rule them all](https://github.com/github/scripts-to-rule-them-all) pattern. Most useful is `./script/bootstrap` which will create a venv and install both the runtime and development related requirements. It will also hook up a pre-commit hook that covers most of what's run by CI.
