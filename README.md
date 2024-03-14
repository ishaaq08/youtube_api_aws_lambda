## About Repo
This repo contains files pertaining to a data pipeline which utilises Python code to extract data from the YouTube API, store it intermediately in a Pandas DataFrame and loads it into an AWS PostgreSQL database. The code was then deployed to 
AWS Lambda and scheduled for execution by AWS EventBridge. Logs were monitored using AWS CloudWatch.

## Methodology

### About the Data
- The data extracted from the YouTube API pertainined to a single YouTube channel, which was defined by passing the channel ID into the API endpoint.
- The data of interest included: videoID, video title and video statistics (view, like and comment count).
- It is also worth noting that as the API response contained large amounts of data it was spread over several pages. Therefore, within the API call a nextPageToken key is contained enabling the user to retrieve the next page of results.
- Although the code to retrieve the subsequent pages of API responses was made, it was commented out to simplify and reduce code execution time, as the focus of the project was not the quantity of results but the engineering of the pipeline.
- Ultimately, the API query parameters (see documentation)[https://developers.google.com/youtube/v3/docs/videos/list] required for this project included:
  - API key
  - channel ID
  - part=snippet,id: The part parameter specifies a comma-separated list of one or more video resource properties that the API response will include. Of the provided resource properties snippet and id were used.
  - order=date: Order the results of the API response via date from newest to oldest.
  - maxResults=10000: limit the maximum number of results to 10,000

### Python script

#### Extraction
- Python's requests module was employed to extract JSON data from the YouTube API. 
- This data was then stored in a Pandas DataFrame.   

#### Loading
- Python's psycopg2 library enabled a connection to be made with the AWS PostgreSQL database.
- The required database tables were created in Python using psycopg's cursor.
- Each row of the Pandas DataFrame was iterated across - rows were either inserted, if containing information regarding new videos, or rows were updated, if containing updated statistics for existing videos.

### Reconfigure code for AWS Lambda function including any project dependencies
- The code was reconfigured to abide by the requirements for an AWS Lambda function e.g. the code must include an explicit lambda_handler function taking in 2 arguments: event and context.
- Although the code was already modular, it was further refined to fulfill these conditions. To view the original code before deployment to AWS Lambda please visit this (repo)[https://github.com/ishaaq08/etl_api_to_cloud_db].
- **VERY IMPORTANT**: When testing the Lambda function in the AWS console 2 common errors were encountered: 1) no module named Pandas was found 2) no module name psycopg2 was found. These dilemmas were resolved through implementing AWS layers.
To resolve the former issue a built-in AWS Layer can be added containing dependencies for Pandas. However, the latter was much more complex. Please read below:

### Deployment Challenges With Psycopg2
When researching for a solution many solutions pointed to the below repo which helpfully reported:

"This is a custom compiled psycopg2 C library for Python. Due to AWS Lambda missing the required PostgreSQL libraries in the AMI image, we needed to compile psycopg2 with the PostgreSQL libpq.so library statically linked libpq library instead of the default dynamic link." - Visit this (repo)[https://github.com/jkehler/awslambda-psycopg2?source=post_page-----db93b2703bf8--------------------------------]
The steps mentioned in the repo were followed, however due to the requirement of Linux commands to compile the libraries, a Linux OS or a proficient emulator must be used. This was attempted through using Ubuntu on WSL however there were many file structure and format incompatabilities. Thus after further research a simpler solution proposed uploading a dependency package for **psycopg2-binary** (same code as psycopg2 but tailored for development and testing and doesn't require a C compiler). However, users did flag that this was not recommended for production. Since this code is only for a portfolio project this could be overlooked. Furthermore, although the psycopg library was altered no changes were required to be made to the code.

### How To Add psycopg2-binary as an AWS Layer
The below steps outline the process involved in retrieving the neccesary files to create the AWS Layer. **On the contrary see the attached python ZIP file containing the psycopg2-binary dependencies**.

1) Visit this (link)[https://pypi.org/project/psycopg2-binary/#files] to download the wheel files for psycopg2-binary.
2) For this project the wheel file chosen was > "psycopg2_binary-2.9.9-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (3.0 MB view hashes) Uploaded Oct 3, 2023 cp312"
3) Move this file from downloads into the chosen directory.
4) Run `pip install wheel` - a Python libary enabling the unpackaging of wheel files (basically ZIP files for Python modules and libraries).
5) From the terminal change into the directory in which the wheel file is saved.
6) Run `wheel unpack {complete-file-name-including-extension}' - for example mine was `wheel unpack psycopg2_binary-2.9.9-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`.
7) Go into the newly created directory - based on the above file name the new folder was called **psycopg2_binary-2.9.9** - and copy all of the folders within.
8) Create a new folder called **python** and paste these folders into this new folder - the parent folder must be called python due to AWS requirements **(or so I think???)**.
9) Zip this folder called python - via powershell change into the directory which contains the python folder (**not into the python directory**) and run `Compress-Archive {path} {destination-path}`.
10) Upload this ZIP file as an AWS layer and add it to the AWS Lambda function.

### Deploy and test code
- The code was then deployed and tested in AWS Lambda, ensuring a JSON response of 200.

### Create a scheduling rule on AWS EventBridge to schedule the execution of the script
- AWS EventBridge was used to define a rule that schedules the execution of the AWS Lambda function.
- AWS CloudWatch can be used to monitor the log files associated with each scheduled execution of the script to ensure smooth operation.
