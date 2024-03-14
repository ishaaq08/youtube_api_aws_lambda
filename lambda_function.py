import os 
import pandas as pd
import requests
from datetime import datetime 
import psycopg2 as ps

def video_details(api_key, video_id):
    
    url = "https://www.googleapis.com/youtube/v3/videos?key="+api_key+"&part=contentDetails,statistics&id="+video_id
    response = requests.get(url).json()
    
    for video_item in response["items"]:
        video_view_count = video_item["statistics"]["viewCount"]
        video_like_count = video_item["statistics"]["likeCount"]
        video_comment_count = video_item["statistics"]["commentCount"]
        
        return video_view_count, video_comment_count, video_like_count

def video_list(api_key, channel_id, next_page_token):

    url ="https://www.googleapis.com/youtube/v3/search?key="+api_key+"&channelId="+channel_id+"&part=snippet,id&order=date&maxResults=10000&pageToken="+next_page_token
    response = requests.get(url).json()
    
    if "nextPageToken" not in response.keys():
        next_page_token = False
    else:
        next_page_token = response["nextPageToken"]

    df = pd.DataFrame(columns=["video_id", "video_title", "upload_date", "view_count", "like_count", "comment_count"])
    
    for video in response["items"]:
    
        if video["id"]["kind"] == "youtube#video":
            video_id = video["id"]["videoId"]
            video_title = video["snippet"]["title"].replace("&#39;", "")
            video_upload_date = video["snippet"]["publishedAt"]\
                                .split("T")[0]\
                                .replace("-", "/")

            video_view_count, video_comment_count, video_like_count = video_details(api_key, video_id)
            new_row = {"video_id": video_id, "video_title": video_title, "upload_date": video_upload_date, "view_count": video_view_count, "like_count": video_like_count, "comment_count": video_comment_count}
            df.loc[len(df)] = new_row
            
    return df, next_page_token


def retrieve_pages(api_key, channel_id, next_page_token=""):
    
        
    df, next_page_token = video_list(api_key, channel_id, next_page_token)
    main_df = df
    
    # Uncomment the below function to run the next page of the API response
    # while next_page_token:
    #     df, next_page_token = video_list(api_key, channel_id, next_page_token) 
    #     main_df = pd.concat([main_df, df], ignore_index=True)
    #     main_df.reset_index(drop=True, inplace=True)
        
    return main_df



def connect_to_db(host, database, port, user, password):
    try:
        conn = ps.connect(host=host, database=database, port=port, user=user, password=password)
    except ps.OperationalError as e:
        raise e
    else:
        print("Successfully connected to database!")
    return conn

def create_table(curr):
    create_table_command = ("""CREATE TABLE IF NOT EXISTS video(
                            video_id TEXT PRIMARY KEY,
                            video_title TEXT,
                            upload_date DATE,
                            view_count INT,
                            like_count INT,
                            comment_count INT)""")
    
    curr.execute(create_table_command)

def update_rows(curr,row):
    sql = """UPDATE
                video
            SET
                view_count = %s,
                like_count = %s,
                comment_count = %s
            WHERE
                video_id = %s;"""
    
    curr.execute(sql, (row["view_count"], row["like_count"], row["comment_count"], row["video_id"]))

def insert_rows(curr, row):
    sql = """INSERT INTO 
                video(video_id, video_title, upload_date, view_count, like_count, comment_count)
            VALUES (%s, %s, %s, %s, %s, %s);"""
    
    curr.execute(sql, (row["video_id"], row["video_title"], row["upload_date"], row["view_count"], row["like_count"], row["comment_count"]))


def update_or_insert_to_clouddb(dataframe,curr, conn):
    for index,row in dataframe.iterrows():

        curr.execute("""SELECT 
                            *
                        FROM
                            video
                        WHERE
                            video_id = %s;
                        """, (row["video_id"],))

        if curr.fetchone():
            update_rows(curr, row)

        else:
            insert_rows(curr, row)

    conn.commit()


def lambda_handler(event, context):
    api_key = os.environ["API_KEY"]
    channel_id = "UCP7WmQ_U4GB3K51Od9QvM0w"
    host = os.environ["HOST"]
    user = os.environ["USER"]
    password = os.environ["PASSWORD"]
    database = os.environ["DATABASE"]
    port = '5432'

    conn = connect_to_db(host, database, port, user, password)
    curr = conn.cursor()
    
    create_table(curr)
    
    conn.commit()

    results = retrieve_pages(api_key, channel_id)

    update_or_insert_to_clouddb(results,curr, conn)

    now = datetime.now()
    dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
    curr.execute("""INSERT INTO api_schedule(ran_at) VALUES(%s);""", (dt_string,))
    conn.commit()
    
    curr.close()
    conn.close()

    return {
        "status code": 200,
        "body": "Execution completed successfully!"
    }