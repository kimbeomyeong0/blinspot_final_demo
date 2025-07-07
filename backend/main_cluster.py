import os
import pandas as pd
from supabase.client import create_client
from dotenv import load_dotenv
from openai import OpenAI
from sklearn.cluster import DBSCAN
import numpy as np
import json
from tqdm import tqdm
from datetime import datetime
import argparse
import tiktoken
import subprocess
import glob

# 1. 환경 변수 로드 및 설정
load_dotenv()
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL과 SUPABASE_ANON_KEY 환경 변수를 설정해주세요.")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY 환경 변수를 설정해주세요.")

client = OpenAI(api_key=OPENAI_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. DB에서 기사 데이터 불러오기 (media_outlet_id 포함)
def fetch_articles():
    response = supabase.table('articles').select('id, title, content, category, media_outlet_id, url').execute()
    df = pd.DataFrame(response.data)
    print(f"✅ {len(df)}개 기사 로드 완료")
    
    # 중복 제거 적용
    df_deduped = remove_duplicate_articles(df)
    print(f"🧹 중복 제거 후: {len(df_deduped)}개 기사 ({len(df) - len(df_deduped)}개 중복 제거)")
    
    return df_deduped

# 언론사 정보 로드 (id→name, id→bias)
def fetch_media_outlets():
    response = supabase.table('media_outlets').select('id, name, bias').execute()
    mapping = {}
    for row in response.data:
        mapping[row['id']] = {'name': row['name'], 'bias': row['bias']}
    return mapping

# 중복 기사 제거 함수들
def calculate_title_similarity(title1, title2):
    """제목 간 유사도 계산 (Jaccard 유사도 사용)"""
    import re
    
    # 특수문자 제거하고 단어 단위로 분리
    def tokenize(text):
        text = re.sub(r'[^\w\s]', '', str(text).lower())
        return set(text.split())
    
    tokens1 = tokenize(title1)
    tokens2 = tokenize(title2)
    
    if len(tokens1) == 0 and len(tokens2) == 0:
        return 1.0
    if len(tokens1) == 0 or len(tokens2) == 0:
        return 0.0
    
    intersection = len(tokens1.intersection(tokens2))
    union = len(tokens1.union(tokens2))
    
    return intersection / union if union > 0 else 0.0

def remove_duplicate_articles(df, title_similarity_threshold=0.8):
    """
    중복 기사 제거:
    1. URL 기반 완전 중복 제거
    2. 제목 유사도 기반 중복 제거 (같은 이슈를 다룬 기사들)
    """
    if len(df) == 0:
        return df
    
    print(f"🔍 중복 제거 시작 (총 {len(df)}개 기사)")
    
    # 1단계: URL 기반 완전 중복 제거
    df_url_deduped = df.drop_duplicates(subset=['url'], keep='first')
    url_removed = len(df) - len(df_url_deduped)
    if url_removed > 0:
        print(f"   📎 URL 중복 제거: {url_removed}개")
    
    # 2단계: 카테고리별로 제목 유사도 기반 중복 제거
    result_dfs = []
    
    for category in df_url_deduped['category'].unique():
        if pd.isna(category):
            continue
            
        cat_df = df_url_deduped[df_url_deduped['category'] == category].copy()
        if len(cat_df) <= 1:
            result_dfs.append(cat_df)
            continue
        
        print(f"   🗂️ [{category}] 카테고리: {len(cat_df)}개 기사")
        
        # 제목 유사도 기반 그룹핑
        to_remove = set()
        articles = cat_df.reset_index(drop=True)
        
        for i in range(len(articles)):
            if i in to_remove:
                continue
                
            current_title = articles.loc[i, 'title']
            current_media = articles.loc[i, 'media_outlet_id']
            
            # 이후 기사들과 비교
            for j in range(i+1, len(articles)):
                if j in to_remove:
                    continue
                    
                compare_title = articles.loc[j, 'title']
                compare_media = articles.loc[j, 'media_outlet_id']
                
                # 같은 언론사면 스킵 (언론사 내 중복은 URL로 이미 처리됨)
                if current_media == compare_media:
                    continue
                
                similarity = calculate_title_similarity(current_title, compare_title)
                
                if similarity >= title_similarity_threshold:
                    # 유사한 기사 발견 - 더 긴 본문을 가진 기사를 유지
                    current_content_len = len(str(articles.loc[i, 'content']))
                    compare_content_len = len(str(articles.loc[j, 'content']))
                    
                    if compare_content_len > current_content_len:
                        to_remove.add(i)
                        print(f"      🔄 유사 제목 발견 (유사도: {similarity:.2f})")
                        print(f"         제거: {current_title[:50]}...")
                        print(f"         유지: {compare_title[:50]}...")
                        break
                    else:
                        to_remove.add(j)
                        print(f"      🔄 유사 제목 발견 (유사도: {similarity:.2f})")
                        print(f"         유지: {current_title[:50]}...")
                        print(f"         제거: {compare_title[:50]}...")
        
        # 제거할 기사들 제외하고 남은 기사들 추가
        filtered_articles = articles.drop(index=list(to_remove))
        result_dfs.append(filtered_articles)
        
        title_removed = len(to_remove)
        if title_removed > 0:
            print(f"      ➡️ 제목 유사도 기반 제거: {title_removed}개")
    
    # 모든 카테고리 결과 합치기
    final_df = pd.concat(result_dfs, ignore_index=True) if result_dfs else pd.DataFrame()
    
    total_removed = len(df) - len(final_df)
    print(f"✅ 총 {total_removed}개 중복 기사 제거 완료")
    
    return final_df

# 3. 임베딩 생성 (OpenAI text-embedding-3-small)
def get_embeddings(texts, model="text-embedding-3-small", cache=None, batch_size=256):
    embeddings = []
    if cache is None:
        cache = {}
    n = len(texts)
    for i in range(0, n, batch_size):
        batch = texts[i:i+batch_size]
        batch_embeddings = []
        uncached_idx = []
        uncached_texts = []
        # 캐시 확인
        for idx, text in enumerate(batch):
            if text in cache:
                batch_embeddings.append(cache[text])
            else:
                batch_embeddings.append(None)
                uncached_idx.append(idx)
                uncached_texts.append(text)
        # uncached만 batch로 임베딩 요청
        if uncached_texts:
            try:
                res = client.embeddings.create(input=uncached_texts, model=model)
                for j, emb in enumerate(res.data):
                    cache[uncached_texts[j]] = emb.embedding
                    batch_embeddings[uncached_idx[j]] = emb.embedding
            except Exception as e:
                print(f"❌ 임베딩 실패(batch): {e}")
                for j in uncached_idx:
                    batch_embeddings[j] = [0.0]*1536
        embeddings.extend(batch_embeddings)
    return np.array(embeddings)

# 4. 클러스터링 (DBSCAN)
def cluster_embeddings(embeddings, eps=0.5, min_samples=3):
    db = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    labels = db.fit_predict(embeddings)
    return labels

# 5. 클러스터 대표 이슈 요약 (gpt-3.5-turbo)
def summarize_cluster(df_cluster, model="gpt-3.5-turbo", max_tokens=300, max_articles=12, chunk_size=6000):
    enc = tiktoken.encoding_for_model(model)
    # 1. 언론사/편향별 고른 샘플링
    sampled = []
    # 우선 bias별 그룹핑
    for bias in ['left', 'center', 'right']:
        group = df_cluster[df_cluster['media_outlet_id'].notnull() & (df_cluster['media_outlet_id'] != '')]
        group = group[df_cluster['bias'] == bias] if 'bias' in df_cluster else df_cluster
        group = group.sample(min(len(group), max_articles//3), random_state=42) if len(group) > 0 else pd.DataFrame()
        sampled.append(group)
    sampled_df = pd.concat(sampled) if sampled else df_cluster.sample(min(len(df_cluster), max_articles), random_state=42)
    # 2. 기사별로 제목+본문 일부만 추출
    def make_text(row):
        title = str(row['title'])
        content = str(row['content'])[:1000]
        return f"[제목] {title}\n[본문] {content}"
    texts = [make_text(row) for _, row in sampled_df.iterrows()]
    # 3. context 초과 방지: 토큰 길이 체크 및 자르기
    prompt_head = "다음 뉴스 기사들을 대표하는 이슈에 대해, 처음 보는 사람도 이해할 수 있도록 4~5문단 이상의 풍부한 설명, 배경, 주요 쟁점까지 포함해 자세히 요약해줘:\n"
    joined = "\n\n".join(texts)
    tokens = len(enc.encode(prompt_head + joined))
    # 너무 길면 chunk별 부분 요약 후 합치기
    if tokens > 14000:
        # chunk 단위로 나눠 부분 요약
        chunked = []
        cur = []
        cur_tokens = 0
        for t in texts:
            t_tokens = len(enc.encode(t))
            if cur_tokens + t_tokens > chunk_size:
                chunked.append(cur)
                cur = []
                cur_tokens = 0
            cur.append(t)
            cur_tokens += t_tokens
        if cur:
            chunked.append(cur)
        partial_summaries = []
        for chunk in chunked:
            prompt = prompt_head + "\n\n".join(chunk)
            try:
                res = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.4
                )
                content = getattr(res.choices[0].message, "content", None)
                if content:
                    partial_summaries.append(content.strip())
            except Exception as e:
                print(f"❌ 부분 요약 실패: {e}")
        # 부분 요약 합쳐서 최종 요약
        final_prompt = prompt_head + "\n\n".join(partial_summaries)
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": final_prompt}],
                max_tokens=max_tokens,
                temperature=0.4
            )
            content = getattr(res.choices[0].message, "content", None)
            if content:
                return content.strip()
            else:
                return "요약 실패"
        except Exception as e:
            print(f"❌ 최종 요약 실패: {e}")
            return "요약 실패"
    else:
        prompt = prompt_head + joined
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.4
            )
            content = getattr(res.choices[0].message, "content", None)
            if content:
                return content.strip()
            else:
                return "요약 실패"
        except Exception as e:
            print(f"❌ 요약 실패: {e}")
            return "요약 실패"

# 5-1. 클러스터 대표 제목 생성 (GPT가 직관적이고 흥미로운 제목 생성)
def generate_cluster_title(df_cluster, model="gpt-3.5-turbo", max_tokens=100, max_articles=8):
    """
    클러스터에 포함된 기사들을 분석해서 GPT가 직관적이고 흥미로운 제목을 생성
    """
    enc = tiktoken.encoding_for_model(model)
    
    # 1. 대표 기사들 샘플링 (너무 많으면 토큰 초과)
    sampled_df = df_cluster.sample(min(len(df_cluster), max_articles), random_state=42)
    
    # 2. 기사별로 제목+본문 요약 추출
    def make_text(row):
        title = str(row['title'])
        content = str(row['content'])[:500]  # 제목 생성용이므로 짧게
        return f"• {title}\n  요약: {content[:200]}..."
    
    texts = [make_text(row) for _, row in sampled_df.iterrows()]
    
    # 3. 제목 전용 프롬프트 (summary와 확실히 구분)
    prompt = f"""다음은 같은 이슈에 관한 뉴스 기사들입니다:

{chr(10).join(texts)}

위 기사들의 핵심 이슈를 한눈에 파악할 수 있는 **임팩트 있는 헤드라인**을 만들어주세요.

조건:
- 15-25자의 짧고 강렬한 제목
- 클릭하고 싶게 만드는 표현 (궁금증, 감정 자극)
- "!", "?", "..." 등 특수문자로 강조
- 핵심 키워드 위주로 간결하게
- 뉴스 헤드라인 스타일 (상세 설명 금지)

반드시 제목만 출력하세요:"""

    # 4. 토큰 길이 체크
    tokens = len(enc.encode(prompt))
    if tokens > 3000:  # 너무 길면 기사 수 줄이기
        sampled_df = df_cluster.sample(min(len(df_cluster), 4), random_state=42)
        texts = [make_text(row) for _, row in sampled_df.iterrows()]
        prompt = f"""다음 기사들의 핵심 이슈를 나타내는 임팩트 있는 헤드라인을 15-25자로 생성하세요:

{chr(10).join(texts)}

짧고 강렬한 제목만 출력:"""

    # 5. GPT 호출
    try:
        res = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7  # 창의적인 제목을 위해 조금 높게
        )
        content = getattr(res.choices[0].message, "content", None)
        if content:
            # 생성된 제목 정리 (따옴표, 불필요한 문자 제거)
            title = content.strip().strip('"').strip("'").strip()
            
            # 제목이 너무 길면 자르기
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title if title else "새로운 이슈 발생"
        else:
            return "새로운 이슈 발생"
    except Exception as e:
        print(f"❌ 제목 생성 실패: {e}")
        # 폴백: 기사 제목에서 핵심 키워드 추출 (summary와 완전히 다른 방식)
        if len(df_cluster) > 0:
            # 가장 대표적인 기사 제목을 기반으로 임팩트 있는 제목 생성
            original_title = str(df_cluster['title'].iloc[0])
            
            # 핵심 단어 추출을 위한 간단한 처리
            keywords = []
            common_words = ['기자', '뉴스', '일보', '방송', '취재', '보도', '발표', '기사']
            
            words = original_title.split()
            for word in words:
                if len(word) > 1 and word not in common_words:
                    keywords.append(word)
                    if len(keywords) >= 3:  # 최대 3개 키워드
                        break
            
            if keywords:
                fallback_title = ' '.join(keywords[:2])  # 상위 2개 키워드만
                if len(fallback_title) > 25:
                    fallback_title = fallback_title[:22] + "..."
                return fallback_title + " 이슈!"
            else:
                return original_title[:20] + "... 주목!"
        return "긴급 이슈 발생!"

# 6. 전체 파이프라인 실행
def main(output_path=None, eps_list=None, min_samples_list=None):
    df = fetch_articles()
    # 임베딩 입력 길이 제한(3000자)
    df['text'] = (df['title'] + '\n' + df['content'].fillna('')).str.slice(0, 3000)
    media_map = fetch_media_outlets()
    categories = df['category'].unique()
    # 파라미터 grid
    if eps_list is None:
        eps_list = [0.3, 0.4, 0.5, 0.6, 0.7]
    if min_samples_list is None:
        min_samples_list = [2, 3, 4, 5]
    # 저장 경로 자동 생성
    if output_path is None:
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{now_str}_grid.json"
    all_results = []
    summary_lines = []
    summary_lines.append("| eps | min_samples | category | clusters | noise | total |")
    summary_lines.append("|-----|-------------|----------|----------|-------|-------|")
    # 전체 기사 임베딩 캐싱 (텍스트: 벡터)
    embedding_cache = {}
    # 카테고리별 텍스트 미리 준비
    cat_texts = {cat: df[df['category'] == cat]['text'].tolist() for cat in categories}
    cat_embeddings = {}
    for category in categories:
        texts = cat_texts[category]
        if len(texts) == 0:
            cat_embeddings[category] = np.zeros((0, 1536))
        else:
            print(f"🧠 [{category}] 전체 임베딩 생성 중... (중복 제거, batch)")
            cat_embeddings[category] = get_embeddings(texts, cache=embedding_cache)
    for eps in eps_list:
        for min_samples in min_samples_list:
            print(f"\n==================== [eps={eps}, min_samples={min_samples}] ====================")
            meta = []
            cards = []
            clusters_json = []
            for category in categories:
                print(f"\n🗂️  ===== [카테고리: {category}] =====")
                texts = cat_texts[category]
                embeddings = cat_embeddings[category]
                if len(texts) == 0:
                    print("(해당 카테고리 기사 없음)")
                    continue
                print(f"🔗 클러스터링 중...")
                labels = cluster_embeddings(embeddings, eps=eps, min_samples=min_samples)
                n_total = len(labels)
                n_noise = sum(1 for l in labels if l == -1)
                n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
                print(f"📊 클러스터 개수: {n_clusters} | noise(이상치): {n_noise} | 전체 기사: {n_total}")
                meta.append({
                    'category': category,
                    'n_clusters': n_clusters,
                    'n_noise': n_noise,
                    'n_total': n_total
                })
                # 클러스터별 카드 생성
                for cluster_id in sorted(set(labels)):
                    if cluster_id == -1:
                        continue  # noise 제외
                    idxs = [i for i, l in enumerate(labels) if l == cluster_id]
                    df_cluster = df[(df['category'] == category)].iloc[idxs]
                    bias_counter = {'left': 0, 'center': 0, 'right': 0}
                    for _, row in df_cluster.iterrows():
                        media_info = media_map.get(row['media_outlet_id'], {'name': 'Unknown', 'bias': 'unknown'})
                        bias = media_info['bias']
                        if bias in bias_counter:
                            bias_counter[bias] += 1
                    total = sum(bias_counter.values())
                    bias_percent = {k: (v, v/total*100 if total else 0) for k, v in bias_counter.items()}
                    bar = '🟥'*int(bias_percent['left'][1]//5) + '⬜'*int(bias_percent['center'][1]//5) + '🟦'*int(bias_percent['right'][1]//5)
                    # GPT가 클러스터 내용을 분석해서 직관적이고 흥미로운 제목 생성
                    print(f"🎯 클러스터 #{cluster_id+1} 제목 생성 중...")
                    cluster_title = generate_cluster_title(df_cluster)
                    print(f"✨ 생성된 제목: {cluster_title}")
                    
                    summary = summarize_cluster(df_cluster)
                    card_lines = []
                    card_lines.append(f"🏷️ 카테고리: **{category}** | 클러스터 #{cluster_id+1}\n")
                    card_lines.append(f"### 🏷️ 이슈 제목\n**{cluster_title}**\n")
                    card_lines.append("========================================\n")
                    card_lines.append(f"#### 🧠 대표 이슈 요약\n\n**{summary}**\n")
                    card_lines.append("========================================\n")
                    card_lines.append(f"#### 📰 포함된 기사들 (총 {len(df_cluster)}개)\n")
                    card_lines.append(f"#### 📊 편향 게이지\n{bar}\nleft: {bias_counter['left']} ({round(bias_percent['left'][1],1)}%) | center: {bias_counter['center']} ({round(bias_percent['center'][1],1)}%) | right: {bias_counter['right']} ({round(bias_percent['right'][1],1)}%)\n")
                    card_text = "\n".join(card_lines)
                    cards.append({'category': category, 'card_text': card_text})
                    # JSON용 클러스터 정보 추가
                    clusters_json.append({
                        'category': category,
                        'title': cluster_title,
                        'summary': summary,
                        'article_count': len(df_cluster),
                        'bias_left': bias_counter['left'],
                        'bias_center': bias_counter['center'],
                        'bias_right': bias_counter['right'],
                        'article_ids': df_cluster['id'].tolist()
                    })
                summary_lines.append(f"| {eps} | {min_samples} | {category} | {n_clusters} | {n_noise} | {n_total} |")
            all_results.append({
                'eps': eps,
                'min_samples': min_samples,
                'meta': meta,
                'cards': cards
            })
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({'results': all_results}, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 자동 파라미터 탐색 결과가 {output_path}에 저장되었습니다!")
    # summary_table.txt로 표 저장
    with open("summary_table.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))
    print("✅ 파라미터별 클러스터링 결과 요약표가 summary_table.txt에 저장되었습니다!")
    # JSON 결과도 함께 저장
    json_output_path = output_path.replace('.json', '.json')
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump({'clusters': clusters_json}, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 최종본(이슈 카드 TXT)이 {output_path}에, JSON이 {json_output_path}에 저장되었습니다!")

def main_single(output_path=None, eps=0.3, min_samples=3):
    df = fetch_articles()
    df['text'] = (df['title'] + '\n' + df['content'].fillna('')).str.slice(0, 3000)
    media_map = fetch_media_outlets()
    categories = df['category'].unique()
    if output_path is None:
        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = "backend/results"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{now_str}_final.txt")
    # 임베딩 캐싱 및 batch 처리
    embedding_cache = {}
    cat_texts = {cat: df[df['category'] == cat]['text'].tolist() for cat in categories}
    cat_embeddings = {}
    for category in categories:
        texts = cat_texts[category]
        if len(texts) == 0:
            cat_embeddings[category] = np.zeros((0, 1536))
        else:
            print(f"🧠 [{category}] 전체 임베딩 생성 중... (중복 제거, batch)")
            cat_embeddings[category] = get_embeddings(texts, cache=embedding_cache)
    cards = []
    clusters_json = []
    for category in categories:
        print(f"\n🗂️  ===== [카테고리: {category}] =====")
        texts = cat_texts[category]
        embeddings = cat_embeddings[category]
        if len(texts) == 0:
            print("(해당 카테고리 기사 없음)")
            continue
        print(f"🔗 클러스터링 중...")
        labels = cluster_embeddings(embeddings, eps=eps, min_samples=min_samples)
        n_total = len(labels)
        n_noise = sum(1 for l in labels if l == -1)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"📊 클러스터 개수: {n_clusters} | noise(이상치): {n_noise} | 전체 기사: {n_total}")
        # 클러스터별 카드 생성
        for cluster_id in sorted(set(labels)):
            if cluster_id == -1:
                continue  # noise 제외
            idxs = [i for i, l in enumerate(labels) if l == cluster_id]
            df_cluster = df[(df['category'] == category)].iloc[idxs]
            bias_counter = {'left': 0, 'center': 0, 'right': 0}
            for _, row in df_cluster.iterrows():
                media_info = media_map.get(row['media_outlet_id'], {'name': 'Unknown', 'bias': 'unknown'})
                bias = media_info['bias']
                if bias in bias_counter:
                    bias_counter[bias] += 1
            total = sum(bias_counter.values())
            bias_percent = {k: (v, v/total*100 if total else 0) for k, v in bias_counter.items()}
            bar = '🟥'*int(bias_percent['left'][1]//5) + '⬜'*int(bias_percent['center'][1]//5) + '🟦'*int(bias_percent['right'][1]//5)
            # GPT가 클러스터 내용을 분석해서 직관적이고 흥미로운 제목 생성
            print(f"🎯 클러스터 #{cluster_id+1} 제목 생성 중...")
            cluster_title = generate_cluster_title(df_cluster)
            print(f"✨ 생성된 제목: {cluster_title}")
            
            summary = summarize_cluster(df_cluster)
            card_lines = []
            card_lines.append(f"🏷️ 카테고리: **{category}** | 클러스터 #{cluster_id+1}\n")
            card_lines.append(f"### 🏷️ 이슈 제목\n**{cluster_title}**\n")
            card_lines.append("========================================\n")
            card_lines.append(f"#### 🧠 대표 이슈 요약\n\n**{summary}**\n")
            card_lines.append("========================================\n")
            card_lines.append(f"#### 📰 포함된 기사들 (총 {len(df_cluster)}개)\n")
            card_lines.append(f"#### 📊 편향 게이지\n{bar}\nleft: {bias_counter['left']} ({round(bias_percent['left'][1],1)}%) | center: {bias_counter['center']} ({round(bias_percent['center'][1],1)}%) | right: {bias_counter['right']} ({round(bias_percent['right'][1],1)}%)\n")
            card_text = "\n".join(card_lines)
            cards.append({'category': category, 'card_text': card_text})
            # JSON용 클러스터 정보 추가
            clusters_json.append({
                'category': category,
                'title': cluster_title,
                'summary': summary,
                'article_count': len(df_cluster),
                'bias_left': bias_counter['left'],
                'bias_center': bias_counter['center'],
                'bias_right': bias_counter['right'],
                'article_ids': df_cluster['id'].tolist()
            })
    with open(output_path, "w", encoding="utf-8") as f:
        for card in cards:
            f.write(card['card_text'])
            f.write("\n" + ("-"*40) + "\n")
    # JSON 결과도 함께 저장
    json_output_path = output_path.replace('.txt', '.json')
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump({'clusters': clusters_json}, f, ensure_ascii=False, indent=2)
    print(f"\n✅ 최종본(이슈 카드 TXT)이 {output_path}에, JSON이 {json_output_path}에 저장되었습니다!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('output_path', nargs='?', default=None, help='저장할 JSON 경로')
    parser.add_argument('--single', action='store_true', default=True, help='추천 조합(최종본)만 저장')
    args = parser.parse_args()
    if args.single:
        main_single(args.output_path)
    else:
        main(args.output_path)

    # === 자동 DB 업로드 ===
    # 방금 생성된 최신 JSON 파일을 직접 전달
    if args.single:
        # single 모드에서는 방금 생성된 JSON 파일을 사용
        if args.output_path:
            latest_json = args.output_path.replace('.txt', '.json')
        else:
            # output_path가 None이면 main_single에서 생성된 파일 경로 찾기
            result_dir = "backend/results"
            json_files = sorted(glob.glob(os.path.join(result_dir, '*_final.json')), key=os.path.getmtime, reverse=True)
            latest_json = json_files[0] if json_files else None
    else:
        # multi 모드에서는 최신 파일 찾기
        result_dir = os.path.join(os.path.dirname(__file__), 'results')
        json_files = sorted(glob.glob(os.path.join(result_dir, '*_final.json')), key=os.path.getmtime, reverse=True)
        latest_json = json_files[0] if json_files else None
    
    if latest_json and os.path.exists(latest_json):
        print(f"\n🟢 클러스터 결과를 DB에 자동 업로드합니다: {latest_json}")
        try:
            # 기존 이슈 데이터 정리 후 최신 결과 업로드
            subprocess.run(['python3', 'supabase_uploader.py', latest_json], check=True)
        except Exception as e:
            print(f"❌ DB 업로드 자동 실행 실패: {e}")
    else:
        print("❌ 자동 업로드용 클러스터 결과 JSON 파일을 찾을 수 없습니다.") 