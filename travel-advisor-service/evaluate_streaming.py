import requests
import json
import time
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def evaluate_streaming(query, expected_groups):
    """
    Evaluate streaming response quality
    
    Args:
        query: Test query
        expected_groups: List of expected group names
        
    Returns:
        dict with scores and details
    """
    url = "http://localhost:8001/chat/stream"
    payload = {"messages": [{"role": "user", "content": query}], "context": {}}
    
    print(f"\nQuery: {query}")
    print("="*80)
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, stream=True, timeout=60)
        
        if response.status_code != 200:
            print(f"ERROR: Status {response.status_code}")
            return {"score": 0, "error": f"Status {response.status_code}"}
        
        chunks = []
        groups_received = set()
        total_content_length = 0
        first_chunk_time = None
        
        for line in response.iter_lines():
            if line:
                decoded = line.decode('utf-8')
                
                if decoded.startswith('data: '):
                    data_str = decoded[6:]
                    
                    if data_str == "[DONE]":
                        break
                    
                    try:
                        data = json.loads(data_str)
                        elapsed = time.time() - start_time
                        
                        if first_chunk_time is None:
                            first_chunk_time = elapsed
                        
                        chunks.append(data)
                        
                        if 'group' in data:
                            groups_received.add(data['group'])
                            
                        if 'reply' in data and data['reply']:
                            total_content_length += len(data['reply'])
                            
                        # Print chunk info
                        status = data.get('status', 'unknown')
                        group = data.get('group', 'none')
                        reply_len = len(data.get('reply', ''))
                        
                        print(f"  [{elapsed:.1f}s] {status:10} | {group:12} | {reply_len:4} chars")
                        
                    except json.JSONDecodeError:
                        print(f"  JSON error: {data_str[:100]}")
        
        total_time = time.time() - start_time
        
        # Calculate scores
        scores = {}
        
        # 1. Streaming speed (30 points)
        # First chunk within 3s = full points, > 10s = 0 points
        if first_chunk_time:
            speed_score = max(0, 30 - (first_chunk_time - 3) * 3)
            speed_score = min(30, max(0, speed_score))
        else:
            speed_score = 0
        scores['speed'] = round(speed_score, 1)
        
        # 2. Progressive delivery (25 points)
        # More chunks = better, expect at least 3 for trip planning
        chunk_count = len([c for c in chunks if c.get('status') == 'partial'])
        progressive_score = min(25, chunk_count * 5)
        scores['progressive'] = progressive_score
        
        # 3. Content completeness (30 points)
        # Check if expected groups are present
        expected_set = set(expected_groups)
        completeness_score = (len(groups_received & expected_set) / len(expected_set)) * 30
        scores['completeness'] = round(completeness_score, 1)
        
        # 4. Content quality (15 points)
        # Total content length, expect at least 500 chars for trip planning
        quality_score = min(15, (total_content_length / 500) * 15)
        scores['quality'] = round(quality_score, 1)
        
        total_score = sum(scores.values())
        
        print("\n" + "="*80)
        print(f"EVALUATION RESULTS:")
        print(f"  Speed (first chunk {first_chunk_time:.1f}s):     {scores['speed']}/30")
        print(f"  Progressive ({chunk_count} chunks):              {scores['progressive']}/25")
        print(f"  Completeness ({len(groups_received)}/{len(expected_groups)} groups): {scores['completeness']}/30")
        print(f"  Content quality ({total_content_length} chars):  {scores['quality']}/15")
        print(f"  TOTAL SCORE:                      {total_score:.1f}/100")
        print(f"  Total time: {total_time:.1f}s")
        print("="*80)
        
        return {
            "score": total_score,
            "details": scores,
            "chunks": len(chunks),
            "groups": list(groups_received),
            "time": total_time,
            "first_chunk_time": first_chunk_time,
            "content_length": total_content_length
        }
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"score": 0, "error": str(e)}


if __name__ == "__main__":
    test_cases = [
        {
            "query": "Lên kế hoạch du lịch Đà Lạt 3 ngày 2 đêm với mức giá 5 triệu đồng",
            "expected_groups": ["spots", "hotels", "food", "itinerary", "cost"]
        },
        {
            "query": "Gợi ý 5 địa điểm tham quan ở Đà Lạt",
            "expected_groups": ["spots"]
        },
        {
            "query": "Tìm khách sạn ở Đà Lạt giá dưới 1 triệu",
            "expected_groups": ["hotels"]
        }
    ]
    
    print("\n" + "="*80)
    print("STREAMING ENDPOINT EVALUATION")
    print("="*80)
    
    all_scores = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\nTEST CASE {i}/{len(test_cases)}")
        result = evaluate_streaming(test_case["query"], test_case["expected_groups"])
        all_scores.append(result["score"])
        
        time.sleep(2)  # Cool down between tests
    
    avg_score = sum(all_scores) / len(all_scores)
    
    print("\n\n" + "="*80)
    print(f"FINAL AVERAGE SCORE: {avg_score:.1f}/100")
    
    if avg_score >= 70:
        print("PASSED! Streaming quality is good.")
    else:
        print(f"NEEDS IMPROVEMENT. Target: 70/100, Current: {avg_score:.1f}/100")
    
    print("="*80)
