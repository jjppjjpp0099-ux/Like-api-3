from flask import Flask, request, jsonify
import requests
import random

app = Flask(__name__)

def get_flag(region):
    flags = {
        "IND": "🇮🇳"
    }
    return flags.get(region.upper(),"🌍")

@app.route("/like")
def like():

    uid = request.args.get("uid")
    region = request.args.get("server_name","IND").upper()

    if not uid:
        return jsonify({"error":"UID missing"})

    try:

        profile_url = f"https://freefireinfo.vercel.app/api/profile?uid={uid}&region={region}"
        r = requests.get(profile_url,timeout=10)
        data = r.json()

    except:
        return jsonify({"error":"profile fetch failed"})

    if "AccountInfo" not in data:
        return jsonify({"status":0})

    info = data["AccountInfo"]

    name = info.get("Name","Unknown")
    level = info.get("Level",0)
    likes_before = info.get("Likes",0)

    # simulate like sending
    likes_given = random.randint(10,20)

    likes_after = likes_before + likes_given

    response = {

        "basicInfo":{
            "nickname":name,
            "level":level,
            "liked":likes_before,
            "rank":"Heroic"
        },

        "socialInfo":{
            "signature":"Free Fire Player Profile"
        },

        "extra":{
            "likes_before":likes_before,
            "likes_after":likes_after,
            "likes_given":likes_given,
            "flag":get_flag(region)
        },

        "status":1
    }

    return jsonify(response)

@app.route("/")
def home():
    return {"API":"Free Fire Like API Running"}

if __name__ == "__main__":
    app.run()    except requests.exceptions.HTTPError as e:
        print(f"HTTP error in make_profile_check_request for token {token_value[:10]}...: {e.response.status_code} - {e.response.text[:100]}")
    except requests.exceptions.RequestException as e:
        print(f"Request error in make_profile_check_request for token {token_value[:10]}...: {e}")
    except Exception as e:
        print(f"Unexpected error in make_profile_check_request for token {token_value[:10]}... processing response: {e}")
    return None

def decode_protobuf_profile_info(binary_data):
    try:
        items = like_count_pb2.Info()
        items.ParseFromString(binary_data)
        return items
    except Exception as e:
        print(f"Error decoding Protobuf profile data: {e}")
        return None

app = Flask(__name__)

@app.route('/like', methods=['GET'])
def handle_requests():
    uid_param = request.args.get("uid")
    server_name_param = request.args.get("server_name", "").upper()
    use_random = request.args.get("random", "false").lower() == "true"

    if not uid_param or not server_name_param:
        return jsonify({"error": "UID and server_name are required"}), 400

    # Load visit token for profile checking
    visit_tokens = load_tokens(server_name_param, for_visit=True)
    if not visit_tokens:
        return jsonify({"error": f"No visit tokens loaded for server {server_name_param}."}), 500
    
    # Use the first visit token for profile check
    visit_token = visit_tokens[0] if visit_tokens else None
    
    # Load regular tokens for like sending
    all_available_tokens = load_tokens(server_name_param, for_visit=False)
    if not all_available_tokens:
        return jsonify({"error": f"No tokens loaded or token file invalid for server {server_name_param}."}), 500

    print(f"Total tokens available for {server_name_param}: {len(all_available_tokens)}")

    # Get the batch of tokens for like sending
    if use_random:
        tokens_for_like_sending = get_random_batch_tokens(server_name_param, all_available_tokens)
        print(f"Using RANDOM batch selection for {server_name_param}")
    else:
        tokens_for_like_sending = get_next_batch_tokens(server_name_param, all_available_tokens)
        print(f"Using ROTATING batch selection for {server_name_param}")
    
    encrypted_player_uid_for_profile = enc_profile_check_payload(uid_param)
    
    # Get likes BEFORE using visit token
    before_info = make_profile_check_request(encrypted_player_uid_for_profile, server_name_param, visit_token)
    before_like_count = 0
    
    if before_info and hasattr(before_info, 'AccountInfo'):
        before_like_count = int(before_info.AccountInfo.Likes)
    else:
        print(f"Could not reliably fetch 'before' profile info for UID {uid_param} on {server_name_param}.")

    print(f"UID {uid_param} ({server_name_param}): Likes before = {before_like_count}")

    # Determine the URL for sending likes
    if server_name_param == "IND":
        like_api_url = "https://client.ind.freefiremobile.com/LikeProfile"
    elif server_name_param in {"BR", "US", "SAC", "NA"}:
        like_api_url = "https://client.us.freefiremobile.com/LikeProfile"
    else:
        like_api_url = "https://clientbp.ggblueshark.com/LikeProfile"

    if tokens_for_like_sending:
        print(f"Using token batch for {server_name_param} (size {len(tokens_for_like_sending)}) to send likes.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(send_likes_with_token_batch(uid_param, server_name_param, like_api_url, tokens_for_like_sending))
        finally:
            loop.close()
    else:
        print(f"Skipping like sending for UID {uid_param} as no tokens available for like sending.")
        
    # Get likes AFTER using visit token
    after_info = make_profile_check_request(encrypted_player_uid_for_profile, server_name_param, visit_token)
    after_like_count = before_like_count
    actual_player_uid_from_profile = int(uid_param)
    player_nickname_from_profile = "N/A"

    if after_info and hasattr(after_info, 'AccountInfo'):
        after_like_count = int(after_info.AccountInfo.Likes)
        actual_player_uid_from_profile = int(after_info.AccountInfo.UID)
        if after_info.AccountInfo.PlayerNickname:
            player_nickname_from_profile = str(after_info.AccountInfo.PlayerNickname)
        else:
            player_nickname_from_profile = "N/A"
    else:
        print(f"Could not reliably fetch 'after' profile info for UID {uid_param} on {server_name_param}.")

    print(f"UID {uid_param} ({server_name_param}): Likes after = {after_like_count}")

    likes_increment = after_like_count - before_like_count
    request_status = 1 if likes_increment > 0 else (2 if likes_increment == 0 else 3)

    response_data = {
        "LikesGivenByAPI": likes_increment,
        "LikesafterCommand": after_like_count,
        "LikesbeforeCommand": before_like_count,
        "PlayerNickname": player_nickname_from_profile,
        "UID": actual_player_uid_from_profile,
        "status": request_status,
        "Note": f"Used visit token for profile check and {'random' if use_random else 'rotating'} batch of {len(tokens_for_like_sending)} tokens for like sending."
    }
    return jsonify(response_data)

@app.route('/token_info', methods=['GET'])
def token_info():
    """Endpoint to check token counts for each server"""
    servers = ["IND", "BD", "BR", "US", "SAC", "NA"]
    info = {}
    
    for server in servers:
        regular_tokens = load_tokens(server, for_visit=False)
        visit_tokens = load_tokens(server, for_visit=True)
        info[server] = {
            "regular_tokens": len(regular_tokens),
            "visit_tokens": len(visit_tokens)
        }
    
    return jsonify(info)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
