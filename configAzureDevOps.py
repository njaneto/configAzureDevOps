import requests
import base64
import argparse


def getHeaders(pat):
    authorization = str(base64.b64encode(bytes(':' + pat, 'ascii')), 'ascii')
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic ' + authorization
    }
    return headers


def getProject(pat, uri, project_id):
    print("---getProject---")
    endpoint = uri + "/_apis/projects/" + project_id + "?api-version=6.0"
    return send(pat, endpoint, "")


def send(pat, endpoint, data):
    print("---EndPoint: ", endpoint)
    if data == "":
        response = requests.get(endpoint, headers=getHeaders(pat))
    else:
        response = requests.post(endpoint, headers=getHeaders(pat), json=data)

    print("---Status Code", response.status_code)
    print("---JSON Response ", response.json())
    return response


def getRepository(pat, uri, name):
    print("---getRepository---")
    endpoint = uri + "/_apis/git/repositories/" + name + "?api-version=6.0"
    return send(pat, endpoint, "")


def validateRepository(pat, uri, name):
    response = getRepository(pat, uri, name)

    if response.status_code == 200:
        print("##vso[task.logissue type=error] Repository already exists =( !!! ")
        print("##vso[task.complete result=Failed;]DONE")
    else:
        print("##[debug] Repository name does not exist =) !!! ")
        print("##vso[task.complete result=Succeeded;]DONE")


def createRepository(pat, uri, name, project_id):
    print("---createRepository---")
    data = {
        "name": name,
        "project": {
            "id": project_id
        }
    }

    endpoint = uri + "/_apis/git/repositories?api-version=6.0"
    response = send(pat, endpoint, data)

    if response.status_code == 201:
        repository_id = response.json().get("id")
        print("##[debug] repository[ " + repository_id + " ] successfully created =) !!! ")
        print("##vso[task.complete result=Succeeded;]DONE")
    else:
        print("##vso[task.logissue type=error] Could not create repository =( !!! ")
        print("##vso[task.complete result=Failed;]DONE")


def createPipeline(pat, uri, name):
    res = getRepository(pat, uri, name)
    data = {
        "name": name,
        "configuration": {
            "type": "yaml",
            "path": "/azure-pipelines.yml",
            "repository": {
                "id": res.json().get("id"),
                "name": name,
                "type": "azureReposGit"
            }
        }
    }
    print("---createPipeline---")
    endpoint = uri + "/_apis/pipelines?api-version=6.0"
    response = send(pat, endpoint, data)

    if response.status_code == 200:
        pipeline_id = response.json().get("id")
        print("##[debug] pipeline [ " + uri + "/_build?definitionId=" + str(
            pipeline_id) + " ] successfully created =) !!! ")
    else:
        print(
            "##vso[task.logissue type=warning] Could not create pipeline, request configuration manually =( !!! ")
        print("##vso[task.complete result=SucceededWithIssues;]DONE")

    return response


def createPolicy(pat, uri, repository_id):
    data = {
        "isEnabled": "true",
        "isBlocking": "true",
        "isDeleted": "false",
        "type": {
            "id": "fa4e907d-c16b-4a4c-9dfa-4906e5d171dd"
        },
        "settings": {
            "minimumApproverCount": 2,
            "creatorVoteCounts": "false",
            "allowDownvotes": "false",
            "resetOnSourcePush": "true",
            "requireVoteOnLastIteration": "false",
            "resetRejectionsOnSourcePush": "true",
            "blockLastPusherVote": "false",
            "scope": [
                {
                    "repositoryId": repository_id,
                    "refName": "refs/heads/master",
                    "matchKind": "Exact"
                }
            ]
        }
    }

    print("---createPolicy---")
    endpoint = uri + "/_apis/policy/configurations?api-version=6.0"
    response = send(pat, endpoint, data)

    if response.status_code == 200:
        policy_id = response.json().get("id")
        print("##[debug] policy [ " + str(policy_id) + " ] successfully created =) !!! ")
    else:
        print("##vso[task.logissue type=warning] The policy could not be created. Request creation manually =( !!! ")
        print("##vso[task.complete result=SucceededWithIssues;]DONE")


def createBuild(pat, uri, pipeline_id, repository_id):
    data = {
        "isEnabled": "true",
        "isBlocking": "true",
        "type": {
            "id": "0609b952-1397-4640-95ec-e00a01b2c241"
        },
        "settings": {
            "buildDefinitionId": pipeline_id,
            "queueOnSourceUpdateOnly": "true",
            "validDuration": 0.0,
            "scope": [
                {
                    "repositoryId": repository_id,
                    "refName": "refs/heads/master",
                    "matchKind": "Exact"
                }
            ]
        }
    }
    print("---createBuild---")
    endpoint = uri + "/_apis/policy/configurations?api-version=6.0"
    response = send(pat, endpoint, data)

    if response.status_code == 200:
        build_id = response.json().get("id")
        print("##[debug] build [ " + str(build_id) + " ] successfully created =) !!! ")
    else:
        print(
            "##vso[task.logissue type=warning] The build could not be created. Request creation manually =( !!! ")
        print("##vso[task.complete result=SucceededWithIssues;]DONE")


def rumPipeline(pat, uri, pipeline_id):
    data = {
        "resources": {
            "repositories": {
                "self": {
                    "refName": "refs/heads/master"
                }
            }
        }
    }

    print("---rumPipeline---")
    endpoint = uri + "/_apis/pipelines/" + str(pipeline_id) + "/runs?api-version=6.0"
    response = send(pat, endpoint, data)

    if response.status_code == 200:
        print("##vso[task.logissue type=warning] Pipeline started, please request approval from ADMs =) !!! ")
        print("##vso[task.complete result=Succeeded;]DONE")
    else:
        print("##vso[task.logissue type=warning] Could not start pipeline, start manually =( !!! ")
        print("##vso[task.complete result=SucceededWithIssues;]DONE")


def createAndConfigPipeline(pat, uri, name):
    response = createPipeline(pat, uri, name)

    if response.status_code == 200:

        print("---createAndConfigPipeline---")
        pipeline_id = response.json().get("id")
        repository_id = response.json().get("configuration").get("repository").get("id")

        print("---pipeline_id: " + str(pipeline_id))
        print("---repository_id: " + repository_id)

        createPolicy(pat, uri, repository_id)
        createBuild(pat, uri, pipeline_id, repository_id)
        rumPipeline(pat, uri, pipeline_id)

    else:
        print("##vso[task.logissue type=warning] Could not configure pipeline, request configuration manually =( !!! ")
        print("##vso[task.complete result=SucceededWithIssues;]DONE")


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--pat", action="store", type=str, help="Authentication token generated in azure devops PAT")
    parser.add_argument("--org", action="store", type=str, help="Organization url")
    parser.add_argument("--project_id", action="store", type=str, help="Unique project number")
    parser.add_argument("--repo_name", action="store", type=str, help="Repository name")

    parser.add_argument("-v", "--validate_repo", action="store_true", help="Parameter to check if the repository exists")
    parser.add_argument("-c", "--create_repo", action="store_true", help="Parameter to create the repository")
    parser.add_argument("-cp", "--config_pipeline", action="store_true", help="Parameter to create and configure the pipeline")

    args = parser.parse_args()
    response = getProject(args.pat, args.org, args.project_id)
    uri = response.json().get("_links").get("web").get("href")

    if args.validate_repo:
        print("##[debug] Checking if the repository already exists =) !!! ")
        validateRepository(args.pat, uri, args.repo_name)

    if args.create_repo:
        print("##[debug] Creating the repository  =) !!! ")
        createRepository(args.pat, uri, args.repo_name, args.project_id)

    if args.config_pipeline:
        print("##[debug] Creating and configuring the pipeline  =) !!! ")
        createAndConfigPipeline(args.pat, uri, args.repo_name)

    print("The end =)")
