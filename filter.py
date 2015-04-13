import requests
import json
import os
import time
import webbrowser

CF_LANG = "ru"
#CF_LANG = "com"

def request_cf(lang, method, payload, auth_key):
    if auth_key == None:
        r = requests.get("http://codeforces." + lang + "/api/" + method, params=payload)
        if r.status_code != 200:
            print "Codeforces don't response"
            return None
        resp = json.loads(r.text)
        if resp["status"] != "OK":
            print "Error in API method"
            return None
        return resp["result"]

def load_from_file(filename):
    if not os.path.isfile(filename):
        return None
    f = open(filename, "r")
    data = json.loads(f.read())
    f.close()
    if int(time.time()) - int(data["creation_time"]) >= 24 * 60 * 60:
        return None
    return data["data"]

def save_to_file(filename, data):
    f = open(filename, "w")
    f.write(json.dumps({"creation_time" : int(time.time()), "data" : data}))
    f.close()

def get_cf_contests():
    contests = load_from_file("contests.list")
    if contests == None:
        contests = request_cf(CF_LANG, "contest.list", None, None)
        save_to_file("contests.list", contests)

    cf_contests = [x for x in contests if x["type"] == "CF" and 
                   ("Div. 1" in x["name"] or "Div. 2" in x["name"]) and x["phase"] == "FINISHED"]
    return cf_contests

def get_problems():
    problems = load_from_file("problems.list")
    if problems == None:
        problems = request_cf(CF_LANG, "problemset.problems", None, None)
        save_to_file("problems.list", problems)
    return problems

def get_division(contest_name):
    return 1 if "Div. 1" in contest_name else 2

def filter_problems(contests, problems):
    contests_dict = dict()
    for contest in contests:
        contests_dict[contest["id"]] = contest["name"]
    
    filtered_problems = dict()
    for problem, problem_stat in zip(problems["problems"], problems["problemStatistics"]):
        if problem["contestId"] in contests_dict.keys():
            div = get_division(contests_dict[problem["contestId"]])
            ind = "Div. " + str(div) + "/" + problem["index"]
            if not ind in filtered_problems.keys():
                filtered_problems[ind] = []
            filtered_problems[ind].append((problem, problem_stat))
    return filtered_problems

def get_submissions(handle):
    def load_one_more(fr=1):
        return request_cf(CF_LANG, "user.status", {"handle" : handle, "from" : fr}, None)[0]
    submissions = load_from_file(handle + ".submissions")
    if submissions == None:
        submissions = request_cf(CF_LANG, "user.status", {"handle" : handle}, None)
    last_id = submissions[0]["id"]
    fr = 1
    submission = load_one_more(fr)
    while submission["id"] != last_id:
        submissions = [submission] + submissions
        fr += 1
        submission = load_one_more(fr)
    save_to_file(handle + ".submissions", submissions)
    return submissions

def get_problems_status(submissions):
    problems_status = dict()
    for submission in submissions:
        problem_ind = str(submission["problem"]["contestId"]) + submission["problem"]["index"]
        verdict = submission["verdict"]
        if problem_ind in problems_status.keys():
            if problems_status[problem_ind] != "OK" and verdict == "OK":
                problems_status[problem_ind] = verdict
        else:
            problems_status[problem_ind] = verdict
    return problems_status

def get_problem_url(problem):
    return "http://codeforces." + CF_LANG + "/problemset/problem/" + \
            str(problem["contestId"]) + "/" + problem["index"]

def get_status_url(problem):
    return "http://codeforces." + CF_LANG + "/problemset/status/" + \
            str(problem["contestId"]) + "/problem/" + problem["index"]

print "Loading contests..."
contests = get_cf_contests()
print "OK"

print "Loading problems..."
problems = get_problems()
filtered_problems = filter_problems(contests, problems)
print "OK"

for problem_type in sorted(filtered_problems.keys()):
    print problem_type, len(filtered_problems[problem_type]), " problems loaded"

handle = raw_input("Handle: ")
print "Loading submissions for handle ", handle, "..."
submissions = get_submissions(handle)
problems_status = get_problems_status(submissions)
print "OK"

print "Generating page..."
html = open("index.html", "w")

header = open("header.html", "r").read()
html.write(header)

html.write("<ul class='nav nav-tabs' role='tablist'>")

it = 0
for problem_type in sorted(filtered_problems.keys()):
    html.write("<li role='presentation'>")
    html.write("<a href='#" + str(it) + "' role='tab'\
                 data-toggle='tab' aria-controls='" + problem_type + "'>")
    html.write(problem_type + "</a>")
    html.write("</li>")

    it += 1

html.write("</ul>")

html.write("<div class='tab-content'>")
it = 0
for problem_type in sorted(filtered_problems.keys()):
    html.write("<div role='tabpanel' class='tab-pane fade' id='" + str(it) + "'>")
    html.write("<table class='table'>")

    for problem, problem_stat in sorted(filtered_problems[problem_type], 
                                        key=lambda x: x[1]["solvedCount"], reverse=True):
        problem_ind = str(problem["contestId"]) + problem["index"]
        status = "None"
        if problem_ind in problems_status:
            status = problems_status[problem_ind]
        status_class = ""
        if status != "None":
            if status == "OK":
                status_class = "success"
            else:
                status_class = "danger"
        problem_row = "<tr name='" + problem_type + "' class='" + status_class + "'>"
        problem_row += "<td width='90%'><a href='" + get_problem_url(problem) + "'>"
        problem_row += problem["name"] + "</a></td>"
        problem_row += "<td class='float-right'><a href='" + get_status_url(problem) + "'>" 
        problem_row += "<span class='glyphicon glyphicon-user' aria-hidden='true'></span>"
        problem_row += str(problem_stat["solvedCount"]) + "</td>"
        problem_row += "</tr>"

        html.write(problem_row.encode("UTF-8"))

    html.write("</table>")
    html.write("</div>")

    it += 1

html.write("</div>")
footer = open("footer.html", "r").read()
html.write(footer)

webbrowser.open("file://" + os.path.realpath("index.html"))
