import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
try:
    from supabase.client import create_client, Client
except ImportError:
    print("❌ supabase 패키지가 설치되지 않았습니다. 'pip install supabase' 명령어로 설치해주세요.")
    exit(1)
import asyncio
from pathlib import Path
from dotenv import load_dotenv
import glob

# .env 파일 로드
load_dotenv()

class SupabaseUploader:
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        # 환경 변수에서 Supabase 설정 가져오기
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL과 SUPABASE_ANON_KEY 환경 변수를 설정해주세요.")
        
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as e:
            print(f"❌ Supabase 클라이언트 생성 실패: {e}")
            # 간단한 방식으로 재시도
            self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # 언론사 매핑 (크롤러에서 사용하는 이름 → DB의 name)
        self.media_mapping = {
            "hani": "한겨레",
            "chosun": "조선일보", 
            "kbs": "KBS",
            "ytn": "YTN"
        }
        
        # 언론사 ID 캐시
        self.media_outlet_ids = {}
    
    def load_media_outlets(self):
        """언론사 정보를 로드하여 ID 매핑 생성"""
        try:
            response = self.supabase.table('media_outlets').select('id, name').execute()
            
            for outlet in response.data:
                self.media_outlet_ids[outlet['name']] = outlet['id']
            
            print(f"✅ 언론사 정보 로드 완료: {list(self.media_outlet_ids.keys())}")
            
        except Exception as e:
            print(f"❌ 언론사 정보 로드 실패: {e}")
            raise
    
    def load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """JSON 파일 로드"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"✅ JSON 파일 로드 완료: {file_path} ({len(data)}개 기사)")
            return data
            
        except Exception as e:
            print(f"❌ JSON 파일 로드 실패 ({file_path}): {e}")
            return []
    
    def prepare_article_data(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """기사 데이터를 Supabase 형식으로 변환"""
        prepared_data = []
        
        for article in articles:
            try:
                # 언론사 ID 찾기
                source = article.get('source', '')
                # 크롤러 이름을 DB 이름으로 매핑
                mapped_source = self.media_mapping.get(source, source)
                media_outlet_id = self.media_outlet_ids.get(mapped_source)
                
                if not media_outlet_id:
                    print(f"⚠️ 언론사 ID를 찾을 수 없음: {source}")
                    continue
                
                # 데이터 변환
                prepared_article = {
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'content': article.get('content', ''),
                    'media_outlet_id': media_outlet_id,
                    'category': article.get('category', ''),
                    'published_at': self.parse_datetime(article.get('crawled_at')),
                    'created_at': datetime.now().isoformat()
                }
                
                # 필수 필드 검증
                if not prepared_article['title'] or not prepared_article['url']:
                    print(f"⚠️ 필수 필드 누락: {article}")
                    continue
                
                prepared_data.append(prepared_article)
                
            except Exception as e:
                print(f"❌ 기사 데이터 변환 실패: {e}")
                continue
        
        return prepared_data
    
    def parse_datetime(self, date_str: Optional[str]) -> str:
        """날짜 문자열을 ISO 형식으로 변환"""
        if not date_str:
            return datetime.now().isoformat()
        
        try:
            # 다양한 날짜 형식 지원
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
            
            # 파싱 실패 시 현재 시간 반환
            return datetime.now().isoformat()
            
        except Exception:
            return datetime.now().isoformat()
    
    def upload_articles(self, articles: List[Dict[str, Any]], batch_size: int = 100) -> Dict[str, int]:
        """기사 데이터를 Supabase에 업로드"""
        total_articles = len(articles)
        uploaded_count = 0
        failed_count = 0
        
        print(f"📤 {total_articles}개 기사 업로드 시작...")
        
        # 배치 단위로 업로드
        for i in range(0, total_articles, batch_size):
            batch = articles[i:i + batch_size]
            
            try:
                # 중복 체크 (URL 기반)
                urls = [article['url'] for article in batch]
                existing_response = self.supabase.table('articles').select('url').in_('url', urls).execute()
                existing_urls = {item['url'] for item in existing_response.data}
                
                # 중복되지 않은 기사만 필터링
                new_articles = [article for article in batch if article['url'] not in existing_urls]
                
                if not new_articles:
                    print(f"⚠️ 배치 {i//batch_size + 1}: 모든 기사가 이미 존재함")
                    continue
                
                # 업로드 실행
                response = self.supabase.table('articles').insert(new_articles).execute()
                
                batch_uploaded = len(new_articles)
                uploaded_count += batch_uploaded
                
                print(f"✅ 배치 {i//batch_size + 1}: {batch_uploaded}개 기사 업로드 완료")
                
            except Exception as e:
                print(f"❌ 배치 {i//batch_size + 1} 업로드 실패: {e}")
                failed_count += len(batch)
                continue
        
        return {
            'total': total_articles,
            'uploaded': uploaded_count,
            'failed': failed_count,
            'skipped': total_articles - uploaded_count - failed_count
        }
    
    def upload_from_json_files(self, data_dir: str = "../crawler/data/raw") -> Dict[str, Any]:
        """JSON 파일들을 읽어서 Supabase에 업로드"""
        # 언론사 정보 로드
        self.load_media_outlets()
        
        # JSON 파일 목록 가져오기
        data_path = Path(data_dir)
        json_files = list(data_path.glob("*.json"))
        
        if not json_files:
            print(f"❌ JSON 파일을 찾을 수 없습니다: {data_dir}")
            return {}
        
        print(f"📁 {len(json_files)}개 JSON 파일 발견: {[f.name for f in json_files]}")
        
        total_results = {
            'files_processed': 0,
            'total_articles': 0,
            'uploaded_articles': 0,
            'failed_articles': 0,
            'skipped_articles': 0,
            'results_by_source': {}
        }
        
        # 각 JSON 파일 처리
        for json_file in json_files:
            print(f"\n🔄 처리 중: {json_file.name}")
            
            # JSON 데이터 로드
            articles = self.load_json_file(str(json_file))
            if not articles:
                continue
            
            # 데이터 변환
            prepared_articles = self.prepare_article_data(articles)
            if not prepared_articles:
                print(f"⚠️ 변환된 기사가 없습니다: {json_file.name}")
                continue
            
            # 업로드 실행
            result = self.upload_articles(prepared_articles)
            
            # 결과 집계
            source_name = json_file.stem.replace('_20250705', '')  # 파일명에서 언론사명 추출
            total_results['results_by_source'][source_name] = result
            total_results['files_processed'] += 1
            total_results['total_articles'] += result['total']
            total_results['uploaded_articles'] += result['uploaded']
            total_results['failed_articles'] += result['failed']
            total_results['skipped_articles'] += result['skipped']
        
        return total_results
    
    def print_summary(self, results: Dict[str, Any]):
        """업로드 결과 요약 출력"""
        print("\n" + "="*50)
        print("📊 업로드 결과 요약")
        print("="*50)
        
        print(f"처리된 파일: {results['files_processed']}개")
        print(f"총 기사 수: {results['total_articles']}개")
        print(f"업로드 성공: {results['uploaded_articles']}개")
        print(f"업로드 실패: {results['failed_articles']}개")
        print(f"중복 스킵: {results['skipped_articles']}개")
        
        if results['total_articles'] > 0:
            success_rate = (results['uploaded_articles'] / results['total_articles']) * 100
            print(f"성공률: {success_rate:.1f}%")
        
        print("\n📋 언론사별 결과:")
        for source, result in results['results_by_source'].items():
            print(f"  {source}: {result['uploaded']}/{result['total']}개 업로드")

    def upload_clusters_from_json(self, json_path: Optional[str] = None):
        """클러스터 결과 JSON을 읽어 issues, issue_articles 테이블에 업로드"""
        import json
        from pathlib import Path
        if json_path is None:
            # backend/results/에서 가장 최근 *_final.json 사용
            result_dir = Path(__file__).parent / 'results'
            json_files = sorted(result_dir.glob('*_final.json'), key=lambda x: x.stat().st_mtime, reverse=True)
            if not json_files:
                print('❌ 클러스터 결과 JSON 파일이 없습니다.')
                return
            json_path = str(json_files[0])
        print(f'📂 클러스터 결과 파일: {json_path}')
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        clusters = data.get('clusters', [])
        if not clusters:
            print('❌ 클러스터 데이터가 비어 있습니다.')
            return
        # 업로드 시작
        self.load_media_outlets()  # 혹시 필요할 수 있으니 호출
        issues_uploaded = 0
        issue_articles_uploaded = 0
        for cluster in clusters:
            # issues 테이블에 저장
            title_val = cluster.get('title')
            summary_val = cluster.get('summary')
            title = str(title_val) if title_val is not None else ''
            summary = str(summary_val) if summary_val is not None else ''
            
            # title이 None, 빈 문자열, 공백만 있을 경우 summary 앞부분으로 대체
            if not title or title.strip() == '':
                # summary에서 첫 번째 문장이나 의미 있는 부분 추출
                if summary:
                    # 마침표나 느낌표, 물음표로 끝나는 첫 번째 문장 추출
                    import re
                    sentences = re.split(r'[.!?]', summary)
                    if sentences and sentences[0].strip():
                        title = sentences[0].strip()[:50]  # 50자로 제한
                    else:
                        title = summary[:50].strip()  # 50자로 제한
                else:
                    title = f"{cluster.get('category', '기타')} 관련 이슈"
            
            # 제목이 여전히 비어있다면 기본값 설정
            if not title or title.strip() == '':
                title = f"{cluster.get('category', '기타')} 관련 이슈 #{issues_uploaded + 1}"
            
            issue_insert = {
                'category': cluster.get('category', '기타'),
                'title': title,
                'summary': summary,
                'article_count': cluster.get('article_count', 0),
                'bias_left': cluster.get('bias_left', 0),
                'bias_center': cluster.get('bias_center', 0),
                'bias_right': cluster.get('bias_right', 0),
            }
            try:
                issue_resp = self.supabase.table('issues').insert(issue_insert).execute()
                if not issue_resp.data or not issue_resp.data[0].get('id'):
                    print(f"❌ 이슈 업로드 실패: {issue_insert}")
                    continue
                issue_id = issue_resp.data[0]['id']
                issues_uploaded += 1
                print(f"✅ 이슈 업로드 완료: {title[:30]}...")
            except Exception as e:
                print(f"❌ 이슈 업로드 실패: {e}")
                continue
            # issue_articles 테이블에 저장
            for article_id in cluster.get('article_ids', []):
                try:
                    ia_insert = {'issue_id': issue_id, 'article_id': article_id}
                    self.supabase.table('issue_articles').insert(ia_insert).execute()
                    issue_articles_uploaded += 1
                except Exception as e:
                    print(f"❌ issue_articles 업로드 실패: {e}")
                    continue
        print(f"\n✅ 이슈 {issues_uploaded}개, 이슈-기사 매핑 {issue_articles_uploaded}개 업로드 완료!")


def main():
    """메인 실행 함수"""
    import sys
    try:
        print("🔧 환경 변수 설정 확인...")
        print("SUPABASE_URL과 SUPABASE_ANON_KEY가 설정되어 있는지 확인해주세요.")
        print()
        uploader = SupabaseUploader()
        
        # 명시적으로 클러스터 JSON 파일이 지정된 경우
        if len(sys.argv) > 1:
            cluster_json_path = sys.argv[1]
            print(f"\n🧠 지정된 클러스터(이슈) 결과를 DB에 업로드합니다: {cluster_json_path}")
            uploader.upload_clusters_from_json(cluster_json_path)
            return True
        
        # 크롤링 데이터 업로드 (실패해도 계속 진행)
        try:
            results = uploader.upload_from_json_files()
            uploader.print_summary(results)
        except Exception as e:
            print(f"⚠️ 크롤링 데이터 업로드 실패(무시): {e}")
        # 클러스터 결과 업로드는 항상 실행
        print("\n🧠 클러스터(이슈) 결과도 DB에 업로드합니다...")
        uploader.upload_clusters_from_json()
    except Exception as e:
        print(f"❌ 전체 업로드 실패: {e}")
        return False
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 