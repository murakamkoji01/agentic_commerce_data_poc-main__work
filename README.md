# agentic_commerce_data_poc-main__work

## 何をするのか？ / What is this repository?

このリポジトリは、Agentic Commerce PoC で利用する、全体のプロジェクト`agentic_commerce_data_poc-main`内で処理を行うためのツール群である。c0, c1, c2のデータを作成し、一連の処理を行うためのスクリプト等が含まれる。具体的な処理の手続き、手順等は- [処理の流れ](https://confluence.rakuten-it.com/confluence/spaces/RCPJPSCI/pages/6873616032/Agentic+Commerce+Data+PoC+2)を参照すること。全体のプロジェクトのレポジトリにコピーして利用すること。具体的には、`/path/to/agentic_commerce_data_poc`以下に`work`ディレクトリを作成して、そこにこのリポジトリの中身を全てコピーする。

## 何ができるか / What you can do with scripts?
### 行える処理 / processings

- **対象データの作成(c0, c1, c2)** — 全体プロジェクト内の元データからc0, c1, c2データを作成する
- **属性情報ベースの作成** — 質問を作成するための元とする属性、属性値、その属性値を持つGTINやItemIDをまとめたベースを作成する
- **LLMフィードデータの作成** — LLMにフィードするための、質問と対象のファイルをペアにしたデータを作成<br>
- **LLMによる分類** — LLMにフィードデータを与えて分類結果を取得する<br>
- **LLM分類結果の評価** — LLMによる分離の結果を評価する<br>


## フォルダ構成 / Repository Structure

```text
agentic_commerce_data_poc__work/
├── README.md                                      # この案内
├── src/                                           # スクリプト
├── resources/                                     # 実行時に必要になる言語資源等
├── data/                                          # 実行時データ
│   └── samples/                                   # サンプルデータ
└── .xxxx
```
## ファイル / Files 

- `resources/` — 参照する言語資源
- `src/` — 後処理、および評価用のスクリプト
- `data/` — データ
- `data/smples/` — サンプルデータ

## スクリプトの使い方 / Usage

### データ(c0, c1, c2)作成 / Creating c0, c1, and c2 data
- 基本的なデータ作成。条件がつく場合（感性情報、QAなど）は作成法が異なる
- `aircon`が対象と仮定

```bash
### c0 data : stored files of each product in ./c0 
python3 src/mk_product_info4compare_v2.py 
  -c0 
  -dir ../data/aircon/output_c0/

### c1 data : stored files of each product in ./c1
python3 src/mk_product_info4compare_v2.py 
  -c1 
  -f ../data/aircon/input_c1/100_aircon.json 
  -outdir ./c1

### c2 data : stored files of each product in ./c2
python3 src/mk_product_info4compare_v2.py 
  -c2 
  -dir ../data/aircon/output_gmc_c2/ 
  -outdir ./c2
```

### 属性ベースの作成
- GTIN、ItemIDと属性・属性値をまとめる（商品ベース、属性ベース）
- これでどの属性にどのような値があって、それらを有するGTIN/ItemIDが何かが整理され、これをベースにPseudoユーザ質問を作成する

```bash
src/organize_att.pl -item < ../data/aircon/eav/aircon-full-100/output/silver_attributes.csv > Item_GTIN_Att_Values.tsv
src/organize_att.pl < ../data/aircon/eav/aircon-full-100/output/silver_attributes.csv > Attribute_GTIN_Values_v1.tsv

```

### LLMにフィードするための”質問＋商品情報”ペアを作成
```bash
python3 src/mk_experiment_patterns_v2.py 
  -dir ./c0 
  -f Question100Examples_v1.tsv 
  -out q_c0
  
python3 src/mk_experiment_patterns_v2.py 
  -dir ./c1 
  -f Question100Examples_v1.tsv 
  -out q_c1

python3 src/mk_experiment_patterns_v2.py 
  -dir ./c2 
  -f Question100Examples_v1.tsv 
  -out q_c2
```

### LLMによる分類（対象の商品の情報が、与えられた質問に対してYESかNOか）
- 実際に利用するモデルは可変なので、適宜指定する
```bash
python3 src/llm_asking2productinfo_internal.py 
  -f q_c1/q_001_c0.tsv > expGLM52/res_q001_c1_glm52.tsv 

python3 src/llm_asking2productinfo_gemini.py 
  -f q_c1/q_001_c0.tsv > expGemini35flash/res_q001_c1_gemini35flash.tsv 

python3 src/llm_asking2productinfo.py 
  -f q_c1/q_001_c0.tsv > expGPT54nano/res_q001_c1_gpt54nano.tsv 

python3 src/llm_asking2productinfo_rakutenai.py 
  -f q_c1/q_001_c0.tsv > expRakutenai30/res_q001_c1_rakutenai30.tsv  
```

### LLMによる分類の結果の評価
- Micro (Recall/Precision/Fscore), Macro (Recall/Precision/Fscore)
- 各モデルともにc0/c1/c2のデータを対象に分類しているので、その結果の評価
```bash
python3 src/eval_ac_product2.py 
  -f Question100Examples_v1.tsv 
  -dir expGLM52 
  -type c0 > eval_c0_GLM52.txt

python3 src/eval_ac_product2.py 
  -f Question100Examples_v1.tsv 
  -dir expGLM52 
  -type c1 > eval_c1_GLM52.txt

python3 src/eval_ac_product2.py 
  -f Question100Examples_v1.tsv 
  -dir expGLM52 -type c2 > eval_c2_GLM52.txt
```

## 実行上の注意 / Limitation and Memo

## 参照すべきConfluence / Confluence Pages to Refer

- [スクリプトを使った実際のPoCの記録](https://confluence.rakuten-it.com/confluence/spaces/RCPJPSCI/pages/6873616032/Agentic+Commerce+Data+PoC+2)<br>
 実データを用いてそれぞれのc0/c1/c2データ作成、LLMによる分類、その評価までの手順と評価結果

- [スクリプトを使った実際のPoCの記録（その2）](https://confluence.rakuten-it.com/confluence/spaces/RCPJPSCI/pages/6900390599/Agentic+Commerce+Data+PoC+3+w+Sales+Info.) <br>
 実データを用いてそれぞれのc0/c1/c2データ作成（Sales Info込み）、LLMによる分類、その評価までの手順と評価結果

- [PoC本体](https://ghe.rakuten-it.com/ken-tsuruta/agentic_commerce_data_poc)
 PoC本体のプロジェクトリポジトリ。cloneして使うこと　
