#
# query - uses splicer to simplify complex data manipulations
#

from splicer import Field
import splicer
from splicer.adapters.dict_adapter import DictAdapter

from . import commits
from . import docker
from . import compat

COMMIT_SCHEMA = [
    dict(name="branch", type="STRING"),
    dict(name="commit", type="STRING"),
    dict(name="rel_commit", type="INTEGER")
]

IMAGE_SCHEMA = [
    dict(name="image", type="STRING"),
    dict(name="tag", type="STRING")
]


def images(docker_client, containers):
    all_tags = docker.tags_from_containers(docker_client, containers)
    return [
        dict(image=container.name, tag=tag)
        for container, tags in zip(containers, all_tags)
        for tag in tags
    ]


def branches(source_control):
    return [
        dict(branch=branch.name, commit=commits.hexsha(commit), rel_commit=rel)
        for branch in source_control.branches
        for rel, commit in enumerate(commits.commits(source_control, branch))
    ]


def maxwhen(state, new_v, new_test):
    def key(item):
        v, test = item
        return (
            compat.python2_sort_key(v),
            compat.python2_sort_key(test),
        )
    return max(state, (new_v, new_test), key=key)


def dataset(source_control, docker_client, containers):

    dataset = splicer.DataSet()
    dataset.add_aggregate(
        "maxwhen",
        func=maxwhen,
        returns=Field(name="min", type="STRING"),
        initial=(None, None),
        finalize=lambda state: state[0]
    )

    # data collected at the start of the program
    static_data = DictAdapter(
        branch=dict(
            schema=dict(fields=COMMIT_SCHEMA),
            rows=branches(source_control)
        ),
        image=dict(
            schema=dict(fields=IMAGE_SCHEMA),
            rows=images(docker_client, containers)
        )
    )

    dataset.add_adapter(static_data)

    # splicer doesn't have select distinct yet.. use group by instead
    query = """
    select branch.branch, image, maxwhen(branch.commit,
           branch.rel_commit) as commit,
           max(branch.rel_commit) as rel_commit
    from image join branch on image.tag = branch.commit
    group by branch, image
    union all
    select branch, null as image, branch as commit, -1 from branch
    group by branch
    """

    dataset.create_view(
        'latest_commit',
        query,
    )
    return dataset
