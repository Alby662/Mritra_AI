# linuxone.md — LinuxONE runbook

> **Path in repo:** `deploy/linuxone.md` · **Status:** v0.1 template · Owner: role E
> Record the **exact** commands that worked on the VM, in order, as you go. At 3 a.m. this file is the only memory you have.

## 1. System facts (fill on first login)

| Item | Value |
|---|---|
| Provider | Datathon VM / LinuxONE Community Cloud |
| Hostname / IP | TBD |
| OS and version (`cat /etc/os-release`) | TBD |
| Architecture (`uname -m`) | s390x (expected) |
| Machine generation (`cat /proc/sysinfo \| grep -i type`) | TBD — z16 / LinuxONE 4 or later needed for the AI accelerator |
| vCPUs / RAM / disk (`nproc`, `free -g`, `df -h`) | TBD |
| sudo available? | TBD |
| Outbound internet: PyPI, `icr.io`, GitHub? | TBD |
| Inbound ports allowed | TBD |
| Secure Execution / Hyper Protect available? | TBD (ask organisers on 16 Oct) |
| Access expiry date | TBD |

## 2. Access

```bash
ssh -i ~/.ssh/<key> <user>@<host>
# Tunnel dashboard + enclave to your laptop if inbound ports are closed:
ssh -i ~/.ssh/<key> -L 8501:localhost:8501 -L 8443:localhost:8443 <user>@<host>
```

## 3. Base packages

```bash
# RHEL / CentOS Stream / Fedora-based
sudo dnf install -y git make gcc gcc-c++ cmake python3.11 python3.11-devel podman openssl
# Ubuntu / Debian-based
sudo apt-get update && sudo apt-get install -y git make gcc g++ cmake python3.11 python3.11-venv python3.11-dev podman openssl
```

Record which one you used: TBD

## 4. Python environment (service path only)

```bash
git clone <repo> && cd mritra
python3.11 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements-services.txt    # fastapi uvicorn pydantic httpx pynacl cryptography pandas pyarrow pyyaml
python -c "import fastapi, nacl, cryptography, pandas; print('ok')"
```

**If a wheel is missing on s390x:**

| Package | Symptom | Fix that worked |
|---|---|---|
| `pyarrow` | Build fails | TBD (try `pip install pyarrow --no-binary :all:` with cmake, or run services in the IBM container) |
| `lightgbm` | No wheel | TBD (build from source with cmake, or score with Snap ML instead) |
| `pynacl` / `cryptography` | Needs libsodium / Rust | TBD (`dnf/apt install libsodium-devel` / rustc) |

Keep training dependencies (torch, torch_geometric) **off** the VM.

## 5. IBM Z Accelerated for Snap ML

```bash
podman pull icr.io/ibmz/ibmz-accelerated-for-snapml:<tag-or-digest-from-IBM-page>
podman run --rm -it -v $PWD:/work:Z -w /work icr.io/ibmz/ibmz-accelerated-for-snapml:<tag> \
  python scripts/snapml_timing.py --model results/models/c3_p1_s42.json --n 100000
```

`scripts/snapml_timing.py` loads the exported model, scores N test rows, and prints mean/p50/p99 latency per transaction and throughput. Record results:

| Run | Model | Rows | p50 µs/txn | p99 µs/txn | Throughput | Accelerator used? |
|---|---|---|---|---|---|---|
| 1 | TBD | TBD | TBD | TBD | TBD | TBD |

Reference: https://ibm.github.io/ibm-z-oss-hub/containers/ibmz-accelerated-for-snapml.html

## 6. Demo certificates (mTLS)

```bash
mkdir -p secrets && cd secrets
openssl req -x509 -newkey rsa:3072 -nodes -days 30 -keyout ca.key -out ca.crt -subj "/CN=mritra-demo-ca"
for n in ENCLAVE B0 B1 B2 B3 B4; do
  openssl req -newkey rsa:3072 -nodes -keyout $n.key -out $n.csr -subj "/CN=$n"
  openssl x509 -req -in $n.csr -CA ca.crt -CAkey ca.key -CAcreateserial -days 30 -out $n.crt
done
cd ..
python scripts/gen_bank_keys.py    # NaCl key pairs for B0..B4; writes public keys to configs/banks.yaml
```

`secrets/` is gitignored. Never copy private keys off the VM except to the bank containers that own them.

## 7. Run the services

```bash
pip install podman-compose        # if not packaged
podman-compose -f deploy/compose.yaml build     # builds s390x images natively
podman-compose -f deploy/compose.yaml up -d
curl -k https://localhost:8443/v1/health
curl -k https://localhost:8443/v1/enclave/info   # check attestation.type
python scripts/verify_log.py
```

## 8. Secure Execution path (only if access is granted)

1. Ask organisers for the documented procedure and host-key document for the VM's host.
2. Build the enclave workload image per IBM's Secure Execution / Hyper Protect instructions.
3. Start it; confirm `attestation.type = "secure-execution"` and record the evidence in the log (`ENCLAVE_STARTED`).
4. Record every command here: TBD

If not available: keep the simulated enclave and set the banner (see `DEMO.md`).

## 9. Troubleshooting log

| Time | Problem | Cause | Fix |
|---|---|---|---|
| | | | |

## 10. Tear-down / evidence

- [ ] Screenshots: `uname -m`, services running, `/v1/enclave/info`, Snap ML timing output
- [ ] Copy `tlog.sqlite` and `verify_log.py` output to `results/linuxone/`
- [ ] Note VM expiry; export anything needed before it lapses
