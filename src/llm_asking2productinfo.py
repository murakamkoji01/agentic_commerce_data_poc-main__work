import os
import re
import sys
import csv
from openai import AzureOpenAI
import argparse
import io
import sys
import json
from dotenv import load_dotenv
from pathlib import Path
import openai

# .env ファイルを読み込む
load_dotenv()

# R-Gateway (OPENAI setting)
client = openai.OpenAI(
    # 環境変数からAPIキーを取得
    api_key = os.getenv("GATEWAY_KEY"),  
    base_url="https://api.ai.public.rakuten-it.com/openai/v1"
)

#client = openai.OpenAI(
#    # 環境変数からAPIキーを取得
#    api_key = os.getenv("GATEWAY_KEY"),  
#    base_url="https://api.ai.public.rakuten-it.com/rakutenllms/v1/"
#)

##------- Internal model ---------##
#client = openai.OpenAI(
#    api_key=os.getenv("MDE_KEY"),     ## MDE Key
#    #api_key=os.getenv("MDE_KEY_OLD"), ## OLD Key
#    #api_key=os.getenv("MDE_KEY_OTHER"),   ## Oikawa Key
#    #api_key="sk-2xDId42QTZ9qGvtWWVnpSg",   
#    base_url="https://api-opensource-ai.mde.rakuten-it.com" # LiteLLM Proxy is OpenAI compatible, Read More: https://docs.litellm.ai/docs/proxy/user_keys
#)

def get_instruction_q_target(question, target_info):
    system_role = f"""
あなたは優秀なE-commerce店舗の店長です。
    """

    prompt = f"""
今、ユーザが購入を考えている家電製品（エアコン、冷蔵庫など）についての質問と、ある製品の情報を提示するので、製品の情報が質問に対してYESと言えるかどうかを判定してください。
- 質問はユーザの興味のある製品のなんらかの特徴（キャンセルポリシーや配送情報、設置情報など）が含まれています。
- 製品情報には属性情報、カテゴリ、値段、その他の情報などの様々な情報が含まれています。
- 質問と製品情報を比較して、製品情報が質問のポイントを充足しているなら"YES"、そうでなければ"NO"と答えてください。
- 回答は"YES" / "NO"以外答えないでください。また、他の文字列も出力しないでください。
- 回答は、自信のある時に”YES”として、根拠に乏しい、よくわからないなどの時は”NO"としてください。
- 製品情報はそれほど複雑ではないですが、間違わないように注意深くチェックしてください。
 - 例1
  - 質問: 商品出荷後のキャンセルができないエアコンははどれですか？
  - 製品情報: 製品情報内に、”商品出荷後はキャンセルできかねます”など、の質問に対して”YES"と答えることのできる根拠となる情報がある
  - 判定: "YES"
 - 例2
  - 工事不要と案内されているエアコンはどれですか？
  - 製品情報: 製品情報内に"この商品は設置工事不要です"とった質問に対して”YES"と考えられる根拠情報がある
  - 判定: "YES"    
    
#質問: {question}
#製品情報:
{target_info}

#判定結果
"""
    return system_role, prompt


def _get_instruction_q_target(question, target_info):
    system_role = f"""
あなたは優秀なE-commerce店舗の店長です。
    """

    prompt = f"""
今、ユーザが購入を考えている製品についての質問と、ある製品の情報を提示するので、製品の情報が質問に対してYESと言えるかどうかを判定してください。
- 質問はユーザの興味のある製品のなんらかの特徴（色やサイズなどの属性や値段などの情報）が含まれています
- 製品情報には属性情報、カテゴリ、値段などの様々な情報が含まれています。
- 質問と製品情報を比較して、製品情報が質問のポイントを充足しているなら"YES"、そうでなければ"NO"と答えてください。
- 回答は"YES" / "NO"以外答えないでください。また、他の文字列も出力しないでください。
- 製品情報はそれほど複雑ではないですが、間違わないように注意深くチェックしてください。
 - 例1
  - 質問: 色がメタリックホワイトの冷蔵庫はどれですか？
  - 製品情報: 製品情報内に、”色はメタリックホワイト”という情報がある
  - 判定: "YES"
    
#質問: {question}
#製品情報:
{target_info}

#判定結果
"""
    return system_role, prompt


def get_instruction_get_attvalue(productname, attribute_name, description):

    system_role = f"""
あなたは優秀なE-commerceマーケットアナリストです。
    """

    prompt = f"""
今、「製品タイトル」と「属性名」および「その属性に関する説明」を提示するので、説明に準拠しつつ製品タイトルを見てその属性の属性値と思われる表現があればそれを抽出してください。
- 属性値として考えられる表現には、文字列や数字列、「あり」「なし」などが考えられます。
- 判定は属性値が存在していると判断すればその属性値を、そうでない場合は"NONE"のにしてください。
- 属性値の認識に自信がないときは誤った回答をせずに、”NONE"としてください。    
- 属性に関する説明には「-」を入れろとありますが、あくまで属性値があればそれを、そうでなければ"NONE"にしてください。    
- 製品タイトルは複雑ではありませんが、間違わないように注意深くチェックしてください。
 - 例1
  - 製品タイトル: iseo(イゼオ) クラッグ ターコイズ
  - 属性名: カラー
  - 属性に関する説明: 検索ナビゲーションに利用されるカラーの情報。実際の商品の色に最も近い色を推奨値の中から選択する。複数の値が該当する場合は、どれか1つを選択するか「マルチカラー」を選択する。別項目の「カラー」にはメーカーが公式に発表しているカラーの名称を記載する。メーカーの公式カラーが「クリムゾンレッド」の場合、「カラー」の値は「クリムゾンレッド」となり、「代表カラー」の値は推奨値にある「レッド」となる。「代表カラー」と「カラー」と同じ値になっても構わない。入力値が不明の場合、必須入力時は「-」(半角ハイフン)を入力し、任意入力時は空欄とする。
  - 判定: ターコイズ


#製品タイトル: {productname}
#属性名: {attribute_name}
#属性に関する説明: {description}        
#判定結果
"""
    return system_role,prompt    


def get_instruction_yodobashi_pathcheck(yodobashi, halo):
    
    system_role = f"""
あなたは優秀なE-commerceマーケットアナリストです。
    """

    prompt = f"""
今、別のE-commerceの2つカテゴリパスを提示するので、この2つが同じ意味であるか（同じ製品が存在しそうか）を判定してください。
- もし2つが同じ意味のカテゴリパスであっても、同じパス名とは限らず、多少の違いがあるかもしれないので注意深く観察してください。
 - 例えば、単語が違ったり、多少の単語の非マッチがあるかもしれません。
- 判定は"TRUE"、"FALSE"、または"UNKNOWN"の3種類にしてください。他の文字列は全く出力する必要はありません。
- 共通する単語が数多くても必ずしも2つカテゴリパス名が同じとは限りませんので、注意深くチェックしてください。
 - 例1
  - カテゴリパスA: 家電>リビング･衣類>掃除機>業務・店舗用掃除機
  - カテゴリパスB: 家電 >> 生活家電 >> 業務用掃除機・クリーナー >> 業務用掃除機
  - 判定: TRUE
 - 例2
  - カテゴリパス名A: 家電>理美容家電>スキンケア・フェイスケア>レディースシェーバー 
  - カテゴリパスB: スポーツ・アウトドア >> その他
  - 判定: FALSE

#カテゴリパス名A: {yodobashi}
#カテゴリパス名B: {halo}    
#判定結果
"""
    return system_role,prompt


def get_instruction_yodobashi(yodobashi, product):
    
    system_role = f"""
あなたは優秀なE-commerceマーケットアナリストです。
    """

    prompt = f"""
今、2つの製品名を提示するので、この2つが同じ意味であるか（同じ製品を表す製品名と言えるか）を判定してください。
- もし2つが同じ製品であっても、同じ製品名とは限らず、多少の違いがあるかもしれないので注意深く観察してください。
 - 例えば、語順が違ったり、多少の単語の非マッチがあるかもしれません。
- 判定は"TRUE"、"FALSE"、または"UNKNOWN"の3種類にしてください。他の文字列は全く出力する必要はありません。
- 共通する単語が数多くても必ずしも2つの属性名が同じものを表すとは限りませんので、注意深くチェックしてください。
 - 例1
  - 製品品名A: 山崎実業 YAMAZAKI 3559 [コードレスクリーナースタンド プレート 約W220×D290×H1270mm ホワイト]     
  - 製品品名B: 山崎実業 コードレスクリーナースタンド プレート ホワイト 3559
  - 判定: TRUE
 - 例2
  - 製品名A: 日立 HITACHI CV-SF300 003 [ダストケース 組み(SF300)]    
  - 製品名B: HITACHI サイクロン式掃除機 シャンパンゴールド CV-SF300
  - 判定: FALSE

#商品名A: {yodobashi}
#商品名B: {product}    
#判定結果
"""
    return system_role,prompt


def get_instruction_match_item_product(item_name, product_name):

    system_role = f"""
あなたは優秀なE-commerceマーケットアナリストです。
    """
    prompt = f"""
今、同じ製品を指すと思われる2つの商品名を示すので、この2つが同じ意味であるか（同じ製品を表す製品名と言えるか）を判定してください。
- ’製品’とはある一つのモノを指し、’商品’とは、製品を個別に扱った場合の名前になります。
 - 例えば、’iPhone17ProMax’自体は製品を指しますが、それを店舗A、店舗Bが個別に販売する場合、同じモノを指しますが、値段が違ったりするので、店舗A、店舗Bが同じモノを販売する場合はそれぞれ別商品として考えます。
- 判定は"TRUE"、"FALSE"、または"UNKNOWN"の3種類にしてください。他の文字列は全く出力する必要はありません。
- 共通する単語が数多くても必ずしも2つの属性名が同じものを表すとは限りませんので、注意深くチェックしてください。
 - 例1
  - 商品名A: KT-105 東谷 2WAYコタツテーブル 【暖房器具】AZUMAYA [KT105]
  - 商品名B: 東谷 2WAYこたつ テーブル  KT-105
  - 判定: TRUE
 - 例2
  - 商品名A: 【送料無料】タローズ TARO'S モジュラーケーブル 電話/テレホン フラット 6極4芯 ホワイト 5m エコ簡易パッケージ CMJ-F05WH
  - 商品名B: タローズ モジュラーケーブル CMJ-F05BG
  - 判定: FALSE
    
#商品名A:{item_name}
#商品名B:{product_name}    
#判定結果
"""
    return system_role,prompt


# Function to call GPT model with a prompt
def call_gpt_openai(prompt, system_role):
    
    chat_completion = client.chat.completions.create(
        #model="Rakuten-AI-3.0-Alpha", # model to send
        #model="Qwen3-VL-32B-Instruct",
        #model="DeepSeek-R1",
        #model="DeepSeek-V3",        
        #model="rakutenai-3.0",
        #model="Rakuten-AI-3.0-JP",
        #model="gpt-oss-20b",
        
        #model="gpt-oss-120b",
        #model="gpt-5.6-luna",
        #model="gpt-5.4-nano",
        model="gpt-5.4-mini",
        
        #reasoning_effort="medium",  # low, medium, high から選択
        
        messages = [
            {"role": "user", "content": prompt},
            {"role": "system", "content": system_role},
        ]
    )
    response = chat_completion.choices[0].message.content

    #prompt_tokens = chat_completion.usage.prompt_tokens
    #completion_tokens = chat_completion.usage.completion_tokens    

    prompt_tokens = getattr(chat_completion.usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(chat_completion.usage, "completion_tokens", 0) or 0
    reasoning_tokens = getattr(chat_completion.usage.completion_tokens_details, "reasoning_tokens", 0) or 0

    #print(f'prompt:{prompt_tokens} / completion_tokens:{completion_tokens} / reasoning_tokens:{reasoning_tokens}')
    token_info = str(prompt_tokens)+','+str(completion_tokens)+','+str(reasoning_tokens)

    #print(response)
    return response, token_info



# Function to call GPT model with a prompt
def call_gpt(prompt, system_role):

    chat_completion = client.chat.completions.create(
        #model='rit-gpt', #GPT4o
        #model='gpt-4o-mini',
        model='gpt-4.1-mini',
        messages=[
            {"role": "user", "content": prompt},
            #{"role": "system", "content": ""},
            {"role": "system", "content": system_role},            
        ]
    )
    response = chat_completion.choices[0].message.content
    return response


def query_llm(model, prompt, system_role):
    '''
    
    '''
    completion = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "system", "content": system_role},
        ]
    )
    # print the completion
    #print(completion.choices[0].message.content)
    response = completion.choices[0].message.content
    return response


def row_as_csv_line(row: list[str]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="")
    w.writerow(row)
    return buf.getvalue().rstrip("\r\n")


def get_target_info (tgt_file, flag):

    content = []
    if flag == 'TSV':
        with open(tgt_file, "r", encoding="utf-8", newline='') as f:
            for row in csv.reader(f, delimiter='\t'):
                key = row[0]
                #value = row[1]
                value = re.sub(r'<[^>]+?>', '', row[1])
                value = re.sub(r'\s+',' ',value)
                content.append(value)
                #info = key+"\t"+value
                #content.append(info)
                
        out = "\n".join(content)
        return out
    elif flag == 'JSON':
        with open(tgt_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
            

def main (tgt_file):
    
    with open(tgt_file, "r", encoding="utf-8", newline='') as f:
    #with tgt_file.open(newline="", encoding="utf-8", errors="replace") as f:

        reader = csv.DictReader(f, delimiter="\t")
        #for row in csv.reader(f, delimiter='\t'):
        done = {}

        for row in reader:
            orig_line = "\t".join(row.values())

            question = row.get('Question')
            file_target = row.get('Target_file')            

            if file_target.endswith('.json'):
                target_info = get_target_info (file_target, 'JSON')
            elif file_target.endswith('.tsv'):
                target_info = get_target_info (file_target, 'TSV')
            
            #continue
        
            #system_role, instruction = get_instruction_color(target)
            #system_role, instruction = get_instruction_yodobashi(yodobashi_name, hit_productname)
            #system_role, instruction = get_instruction_get_attvalue(productname, attribute_name, description)
            system_role, instruction = get_instruction_q_target(question, target_info)
            #print(f'===>{system_role}')
            #print(f'--->{instruction}')
            #sys.exit()

            response, token_info = call_gpt_openai(system_role, instruction)
            response = response.lstrip()
            print(f'{response}\t{token_info}\t{orig_line}')
            print(f'{response}\t{token_info}\t{orig_line}',file=sys.stderr)
            #sys.exit()


def _main() -> int:
    root = Path(__file__).resolve().parent.parent
    default_in = root / "res_pairing_itemproduct_appliance.csv"

    ap = argparse.ArgumentParser(description="item_name / productname / 行全体(TSV)")
    ap.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=default_in,
        help=f"入力 CSV（既定: {default_in.name}）",
    )
    args = ap.parse_args()

    if not args.csv_path.is_file():
        print(f"ファイルがありません: {args.csv_path}", file=sys.stderr)
        return 1

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    with args.csv_path.open(newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return 0

    header = rows[0]
    try:
        i_item = header.index("item_name")
        i_prod = header.index("productname")
    except ValueError:
        print("ヘッダに item_name / productname が必要です。", file=sys.stderr)
        return 1

    for row in rows[1:]:
        while len(row) < len(header):
            row.append("")
        item_name = row[i_item] if i_item < len(row) else ""
        product_name = row[i_prod] if i_prod < len(row) else ""
        orig_line = row_as_csv_line(row)
        #sys.stdout.write(f"{name}\t{pname}\t{full}\n")

        system_role, instruction = get_instruction_match_item_product(item_name, product_name)
        #print(f'===>{system_role}')
        #print(f'--->{instruction}')
        #sys.exit()
            
        response = call_gpt_openai(system_role, instruction)
        response = response.lstrip()
        print(f'{response},{orig_line}')
        print(f'{response}\t{orig_line}',file=sys.stderr)
        #sys.exit()                    

    return 0
            
            
def get_newline(row):

    gtin = row[2]
    ptitle = row[3]
    ititle = row[4]
    maker = row[5]
    filterset_code = row[6]
    g1_id = row[7]
    g1_name = row[8]
    g2_id = row[9]
    g2_name = row[10]    

    newline = f"""
GTIN: {gtin}
製品タイトル: {ptitle}
商品タイトル: {ititle}
メーカー名: {maker}
ジャンル: {g1_name} >> {g2_name}
"""
    return newline

    
if __name__ == "__main__":
    #raise SystemExit(main())
    
  parser = argparse.ArgumentParser()
  parser.add_argument('-f', '--file', required=True)    # Target Data file
  args = parser.parse_args()
#
  tgt_file = args.file
#  
  main(tgt_file) # main
    

