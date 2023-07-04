import time, meilisearch


def wait_on(t):
    while client.get_task(t.task_uid).status != "succeeded":
        time.sleep(0.001)

with open("../master_key") as f:
    master_key = f.read().strip()

client = meilisearch.Client('http://127.0.0.1:7700', master_key)

indexes = client.get_all_stats()['indexes'].keys()
for ind in indexes:
    client.delete_index(ind)

client.create_index("index")
client.create_index("index")
client.create_index("index")
index = client.index("index")
index.add_documents([
    {
        'id': 'aaaa-t-s1-s3',
        'title': 'one two',
        'other': 'car bar sonar play',
    },
    {
        'id': 'bbbb-t-s4-s6',
        'title': 'five six',
    }
])
time.sleep(0.1)

print("Find aaaa & bbbb")
print(index.search("aaaa")['hits'][0]["id"])
print(index.search("bbbb"))

print("Update display attributes")
wait_on(index.update_displayed_attributes([]))
print(index.search("bbbb", {'limit': 10000}))

print("Get document")

print(index.get_document('bbbb-t-s4-s6').title)

print(index.get_searchable_attributes())
