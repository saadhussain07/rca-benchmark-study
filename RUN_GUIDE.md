# Run guide, week 1: setup, data, inspection

Run everything inside **Ubuntu on WSL**, not in PowerShell. RCAEval is built
and tested on Ubuntu with Python 3.12, and some of its baselines do not install
on Windows. If you used Docker Desktop for the kind cluster, WSL is probably
already installed.

> **Rule for this week:** RE2 is only *inspected*. RE1 and RE3 are for
> calibration and the pilot. Don't run any detector,
> baseline or model on RE2 until the protocol is frozen. Step 6 is the only
> step that reads RE2, and it reads only the pre-fault part.

## 0. Open Ubuntu

In PowerShell, run `wsl`. If it says WSL is not installed, run
`wsl --install -d Ubuntu-24.04`, restart the computer, open "Ubuntu" from the
Start menu and create a user.

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv python3.12-dev git unzip build-essential graphviz
```

## 1. Folders and RCAEval (pinned version)

```bash
mkdir -p ~/rca && cd ~/rca
git clone https://github.com/phamquiluan/RCAEval.git
cd RCAEval && git checkout 259ea4167160256a74ad30004aa3d96a998c846e && cd ..
```

## 2. Python environment

```bash
cd ~/rca
python3.12 -m venv env
source env/bin/activate
pip install --upgrade pip wheel
pip install -e "./RCAEval[default]"
pip install drain3 groq python-dotenv scipy scikit-learn
# do NOT install pyarrow: it needs NumPy 2, RCAEval pins NumPy 1.26
```

If `drain3` fails with `install_layout`, run
`SETUPTOOLS_USE_DISTUTILS=stdlib pip install drain3`.

Every time you open a new Ubuntu window, run `cd ~/rca && source env/bin/activate` first.

## 3. Study code

Copy `rcastudy.zip` (from the chat) into Ubuntu and unzip it. From Ubuntu,
your Windows Downloads folder is `/mnt/c/Users/<your-windows-name>/Downloads`.

```bash
cd ~/rca
cp /mnt/c/Users/<your-windows-name>/Downloads/rcastudy.zip .
unzip rcastudy.zip
ls rcastudy        # PROTOCOL_V3.md  RUN_GUIDE.md  original  rcastudy  scripts  tests
```

### Quick self-test on fake data (1 minute, no internet)

```bash
cd ~/rca/rcastudy
python tests/make_synthetic.py /tmp/syn
python scripts/03_build_contexts.py --root /tmp/syn --suite re2 --out /tmp/syn/out
python scripts/05_classifiers.py --ctx /tmp/syn/out
python scripts/06_evaluate.py --ctx /tmp/syn/out | head -20
```

You should see a "Detector coverage" table. If you get an error, send me the
last 20 lines.

## 4. Download RE1, RE2 and RE3 (about 5.2 GB, 30–60 min)

The data must sit inside the RCAEval folder, because RCAEval's `main.py`
expects it there:

```bash
cd ~/rca/RCAEval
python -c "from RCAEval.utility import download_re1_dataset, download_re2_dataset, download_re3_dataset; download_re1_dataset(); download_re2_dataset(); download_re3_dataset()"
ls data            # online-boutique  sock-shop-2  train-ticket  RE2  RE3 ...
ls data/RE2        # RE2-OB  RE2-SS  RE2-TT
```

If the download breaks halfway, delete the half-extracted folder (for example
`rm -rf data/RE2/RE2-TT`) and run the same command again.

## 5. Record exactly which data we used

```bash
cd ~/rca/RCAEval
mkdir -p ~/rca/rcastudy/out
python ~/rca/rcastudy/scripts/00_manifest.py data/RE2 > ~/rca/rcastudy/out/data_manifest_re2.txt
python ~/rca/rcastudy/scripts/00_manifest.py data/online-boutique > ~/rca/rcastudy/out/data_manifest_re1ob.txt
wc -l ~/rca/rcastudy/out/data_manifest_re2.txt
```

## 6. Inspect the format (reads only the pre-fault data)

```bash
cd ~/rca/RCAEval
python ~/rca/rcastudy/scripts/01_inspect.py --root data --suite re1 --out ~/rca/rcastudy/out/inspect_re1.txt
python ~/rca/rcastudy/scripts/01_inspect.py --root data --suite re2 --out ~/rca/rcastudy/out/inspect_re2.txt
python ~/rca/rcastudy/scripts/02_select_subsets.py --root data --out ~/rca/rcastudy/out
```

## 7. Send me these files

From `~/rca/rcastudy/out/`, which you can reach in Windows at
`\\wsl$\Ubuntu-24.04\home\<ubuntu-user>\rca\rcastudy\out`:

- `inspect_re1.txt`
- `inspect_re2.txt`
- `pilot_re1.txt`
- `pilot_re3.txt`
- `vote_check_cases.txt`
- the first 5 lines of `data_manifest_re2.txt`, plus its line count

## 8. Groq

1. Open console.groq.com, go to Settings → Limits, and send me a screenshot of the limits for `openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.8-27b`.
2. Don't run any model yet. The pilot comes next week, after I set the CPU unit from your `inspect_re1.txt`.

Then we pilot on 15 RE1 cases, freeze the protocol with a dated GitHub commit,
and start the RE2 runs.
