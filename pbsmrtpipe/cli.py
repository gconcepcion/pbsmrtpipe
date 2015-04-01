import os
import pprint
import sys
import argparse
import logging

from pbsmrtpipe.cli_utils import main_runner, args_executer, validate_file
import pbsmrtpipe
from pbsmrtpipe.exceptions import MalformedEntryStrError
from pbsmrtpipe.models import MetaTask, MetaScatterTask, MetaGatherTask
import pbsmrtpipe.pb_io as IO
import pbsmrtpipe.driver as D
import pbsmrtpipe.tools.utils as TU
from pbsmrtpipe.utils import StdOutStatusLogFilter, setup_log, compose

from pbsmrtpipe.constants import (ENV_PRESET, ENTRY_PREFIX, RX_VALID_BINDINGS, RX_ENTRY, RX_TASK_ID)


log = logging.getLogger()
slog = logging.getLogger('status.' + __file__)


def _validate_preset_xml(path):

    _, _, _, pipelines = __dynamically_load_all()

    if os.path.exists(path):
        _ = IO.parse_pipeline_template_xml(os.path.abspath(path), pipelines)
        return os.path.abspath(path)
    raise IOError("Unable to find preset '{f}'".format(f=path))


def add_log_file_options(p):
    p.add_argument('--log-file', type=str, help="Path to log file")
    return p

LOG_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
LOG_LEVELS_D = {attr: getattr(logging, attr) for attr in LOG_LEVELS}


def add_log_level_option(p):
    p.add_argument('--log-level',
                   default='INFO',
                   choices=LOG_LEVELS, help="Log LEVEL")
    return p


def _add_debug_option(p, message="Print debug output to stdout."):
    p.add_argument('--debug', action='store_true', help=message)
    return p


def _add_mock_option(p):
    p.add_argument('--mock', action='store_true', help=argparse.SUPPRESS)
    return p


def _add_template_id_option(p):
    p.add_argument('template_id', type=str, help="Show details of Pipeline Template.")
    return p


def _add_task_id_option(p):
    p.add_argument('task_id', type=str, help="Show details of registered Task by id.")
    return p


def _validate_dir_or_create(p):
    if os.path.exists(p):
        return p
    else:
        os.mkdir(p)
        return p


def _add_output_dir_option(p):
    p.add_argument('-o', '--output-dir', default=os.getcwd(),
                   type=_validate_dir_or_create,
                   help="Path to job output directory. Directory will be created if it does not exist.")
    return p


def _add_entry_point_option(p):
    p.add_argument('-e', '--entry', dest="entry_points", required=True,
                   action="append",
                   nargs="+", type=_validate_entry, help="Entry Points using 'entry_idX:/path/to/file.txt' format.")
    return p


def _add_preset_xml_option(p):
    p.add_argument('--preset-xml', type=validate_file,
                   help="Preset/Option XML file.")
    return p


def _add_rc_preset_xml_option(p):
    p.add_argument('--preset-rc-xml', type=validate_file,
                   help="Skipping loading preset from ENV var '{x}' and Explicitly load the supplied preset.xml".format(x=ENV_PRESET))
    return p


def _add_output_preset_xml_option(p):
    p.add_argument('-o', '--output-preset-xml', type=str, help="Write pipeline/task preset.xml of options.")
    return p


def pretty_registered_pipelines(registered_new_pipelines_d):

    n = len(registered_new_pipelines_d)
    title = "{n} Registered Pipelines (name -> id)".format(n=n)
    header = len(title) * "*"

    outs = []
    outs.append(header)
    outs.append(title)
    outs.append(header)

    max_name_len = max(len(pipeline.display_name) for pipeline in registered_new_pipelines_d.values())
    pad = 4 + max_name_len

    for i, k in enumerate(registered_new_pipelines_d.values()):
        outs.append(" ".join([(str(i + 1) + ".").rjust(4), k.display_name.ljust(pad), k.idx]))

    return "\n".join(outs)


def pretty_bindings(bindings):
    from pbsmrtpipe.pb_pipelines import Constants

    entry_points = {i for i, o in bindings if i.startswith(ENTRY_PREFIX)}

    s = "*" * 20

    outs = []
    outs.append("Entry points : {n}".format(n=len(entry_points)))
    outs.append(s)

    for i, entry_point in enumerate(entry_points):
        outs.append(entry_point)

    max_length = max(len(i) for i, o in bindings)
    pad = 4

    outs.append("")
    outs.append("Bindings     : {n}".format(n=len(bindings)))
    outs.append(s)

    for i, o in bindings:
        outs.append(" -> ".join([i.rjust(max_length + pad), o]))

    return "\n".join(outs)


def run_show_templates():
    import pbsmrtpipe.loader as L

    print pretty_registered_pipelines(L.load_all_installed_pipelines())

    return 0


def _args_run_show_templates(args):
    return run_show_templates()


def write_task_options_to_preset_xml_and_print(opts, output_file, warning_msg):
    if opts:
        IO.write_schema_task_options_to_xml(opts, output_file)
        print "wrote preset to {x}".format(x=output_file)
    else:
        print warning_msg


def run_show_template_details(template_id, output_preset_xml):

    rtasks, rfiles, operators, pipelines_d = __dynamically_load_all()

    import pbsmrtpipe.bgraph as B

    if template_id in pipelines_d:
        pipeline = pipelines_d[template_id]
        print "Pipeline id   : {i}".format(i=pipeline.idx)
        print "Pipeline name : {x}".format(x=pipeline.display_name)
        print "Description   : {x}".format(x=pipeline.description)
        print pretty_bindings(pipeline.all_bindings)
        if isinstance(output_preset_xml, str):
            rtasks, rfiles, operators, pipelines = __dynamically_load_all()
            task_options = {}
            for b_out, b_in, in pipeline.bindings:
                for x in (b_out, b_in):
                    task_id, _, _ = B.binding_str_to_task_id_and_instance_id(x)
                    task = rtasks.get(task_id, None)
                    if task is None:
                        log.warn("Unable to load task {x}".format(x=task_id))
                    else:
                        for k, v in task.option_schemas.iteritems():
                            task_options[k] = v

            warn_msg = "Pipeline {i} has no options.".format(i=pipeline.idx)
            write_task_options_to_preset_xml_and_print(task_options, output_preset_xml, warn_msg)

    else:
        msg = "Unable to find template id '{t}' in registered pipelines. Use the show-templates option to get a list of workflow options.".format(t=template_id)
        log.error(msg)
        print msg

    return 0


def _args_run_show_template_details(args):
    return run_show_template_details(args.template_id, args.output_preset_xml)


def __dynamically_load_all():
    """ Load the registered tasks and operators

    """
    import pbsmrtpipe.loader as L

    def _f(x):
        """length or None"""
        return "None" if x is None else len(x)

    rtasks, rfile_types, roperators, rpipelines = L.load_all()
    _d = dict(n=_f(rtasks), f=_f(rfile_types), o=_f(roperators), p=_f(rpipelines))
    print "Registry Loaded. Number of MetaTasks:{n} FileTypes:{f} ChunkOperators:{o} Pipelines:{p}".format(**_d)
    return rtasks, rfile_types, roperators, rpipelines


def run_show_tasks():

    r_tasks, _, _, _ = __dynamically_load_all()

    sorted_tasks = sorted(r_tasks.values(), key=lambda x: x.task_id)
    max_id = max(len(t.task_id) for t in sorted_tasks)
    pad = 4
    offset = max_id + pad
    print "Registered Tasks ({n})".format(n=len(sorted_tasks))
    print

    def _to_a(klass):
        d = {MetaTask: "", MetaScatterTask: "(scatter)", MetaGatherTask: "(gather)"}
        return d.get(klass, "")

    for i, t in enumerate(sorted_tasks):
        print " ".join([(str(i + 1) + ".").rjust(3), t.task_id.ljust(offset), _to_a(t) + t.display_name])

    return 0


def _args_run_show_tasks(args):
    return run_show_tasks()


def _print_option_schemas(option_schemas_d):

    def _get_v(oid, s, name):
        return s['properties'][oid][name]

    print "Number of Options {n}".format(n=len(option_schemas_d))
    if option_schemas_d:
        n = 0
        for opt_id, schema in option_schemas_d.iteritems():
            print "Option #{n} Id: {i}".format(n=n, i=opt_id)
            print "\tDefault     : ", _get_v(opt_id, schema, 'default')
            print "\tType        : ", _get_v(opt_id, schema, 'type')
            print "\tDescription : ", _get_v(opt_id, schema, 'description')
            n += 1
            print


def run_show_task_details(task_id):

    r_tasks, _, _, _ = __dynamically_load_all()

    meta_task = r_tasks.get(task_id, None)

    sep = "*" * 20

    if meta_task is None:
        raise KeyError("Unable to find Task id '{i}' Use 'show-tasks' option to list available task ids.".format(i=task_id))
    else:
        print sep
        print meta_task.summary()
        _print_option_schemas(meta_task.option_schemas)

    return 0


def _args_run_show_task_details(args):
    rcode = run_show_task_details(args.task_id)

    output_file = args.output_preset_xml

    if output_file is not None:

        rtasks, _, _, _ = __dynamically_load_all()

        meta_task = rtasks[args.task_id]

        if isinstance(meta_task.option_schemas, dict):
            opts = meta_task.option_schemas
        elif isinstance(meta_task.option_schemas, (list, tuple)):
            # DI list
            opts = meta_task.option_schemas[0]
        else:
            raise TypeError("Malformed task {t}".format(t=meta_task))

        write_task_options_to_preset_xml_and_print(opts, output_file, "WARNING. Task {i} has no task options. NO preset was wrote to a preset.xml file.".format(i=args.task_id))

    return rcode


def _cli_entry_point_args_to_dict(args_entry_points):
    # argparse is kinda stupid, or I don't know how to use the API
    # entry_points=[[('entry_idX', 'docs/index.rst')], [('entry_2', 'docs/wf_example.py')]]
    ep_d = {}
    for elist in args_entry_points:
        for k, v in elist:
            if k in ep_d:
                sys.stderr.write(pprint.pformat(args_entry_points) + "\n")
                raise ValueError("entry point id '{i}' was given multiple times ".format(i=k))
            ep_d[k] = v
    return ep_d


def _args_run_pipeline(args):

    if args.debug:
        slog.debug(args)


    ep_d = _cli_entry_point_args_to_dict(args.entry_points)

    registered_tasks_d, registered_files_d, chunk_operators, pipelines_d = __dynamically_load_all()

    return D.run_pipeline(pipelines_d, registered_files_d, registered_tasks_d, chunk_operators,
                          args.pipeline_template_xml,
                          ep_d, args.output_dir, args.preset_xml, args.preset_rc_xml, args.mock)


def get_base_parser():
    desc = "Description of pbsmrtpipe {v}".format(v=pbsmrtpipe.get_version())
    p = argparse.ArgumentParser(version=pbsmrtpipe.get_version(), description=desc)
    return p


def _validate_entry_id(e):
    m = RX_ENTRY.match(e)
    if m is None:
        msg = "Entry point '{e}' should match pattern {p}".format(e=e, p=RX_ENTRY.pattern)
        raise MalformedEntryStrError(msg)
    else:
        return m.groups()[0]


def _validate_entry(e):
    """
    Validate that entry has the CLI form "entry_id:/path/to/file.txt"

    :raises ValueError, IOError
    """
    if ":" in e:
        x = e.split(":")
        if len(x) == 2:
            entry_id, path = x[0].strip(), x[1].strip()
            if os.path.isfile(path):
                return entry_id, os.path.abspath(path)
            else:
                raise IOError("Unable to find path '{p}' for entry id '{i}'".format(p=path, i=entry_id))

    raise ValueError("Invalid entry id '{e}' format. Expected ('entry_idX:/path/to/file.txt')".format(e=e))


def __add_pipeline_parser_options(p):
    funcs = [_add_debug_option, _add_output_dir_option,
             _add_entry_point_option, _add_preset_xml_option,
             _add_rc_preset_xml_option,
             _add_mock_option]
    f = compose(*funcs)
    return f(p)


def add_pipline_parser_options(p):
    p.add_argument('pipeline_template_xml', type=validate_file,
                   help="Path to pipeline template XML file.")
    p = __add_pipeline_parser_options(p)
    return p


def add_pipeline_id_parser_options(p):
    p.add_argument('pipeline_id', type=str,
                   help="Registered pipeline id (run show-templates) to show a list of the registered pipelines.")
    p = __add_pipeline_parser_options(p)
    return p


def add_show_template_details_parser_options(p):
    p = _add_template_id_option(p)
    p = _add_output_preset_xml_option(p)
    return p


def add_task_parser_options(p):
    _add_debug_option(p)
    funcs = [_add_task_id_option, _add_entry_point_option, _add_output_dir_option,
             _add_preset_xml_option, _add_rc_preset_xml_option,
             _add_mock_option]
    f = compose(*funcs)
    return f(p)


def _args_task_runner(args):
    if args.debug:
        log.info(args)

    registered_tasks, registered_file_types, chunk_operators, pipelines = __dynamically_load_all()
    ep_d = _cli_entry_point_args_to_dict(args.entry_points)
    # the code expects entry: version
    ee_pd = {'entry:' + ei: v for ei, v in ep_d.iteritems() if not ei.startswith('entry:')}

    return D.run_single_task(registered_file_types, registered_tasks, chunk_operators, ee_pd, args.task_id, args.output_dir, args.preset_xml, args.preset_rc_xml)


def _args_run_show_workflow_level_options(args):

    from pbsmrtpipe.pb_io import REGISTERED_WORKFLOW_OPTIONS

    _print_option_schemas(REGISTERED_WORKFLOW_OPTIONS)

    output_file = args.output_preset_xml

    if output_file is not None:
        xml = IO.schema_workflow_options_to_xml(REGISTERED_WORKFLOW_OPTIONS)
        with open(output_file, 'w') as w:
            w.write(str(xml))
        log.info("wrote options to {x}".format(x=output_file))

    return 0


def add_show_task_options(p):
    p = _add_task_id_option(p)
    p = _add_output_preset_xml_option(p)
    return p


def _args_run_pipeline_id(args):

    registered_tasks_d, registered_files_d, chunk_operators, pipelines = __dynamically_load_all()

    if args.pipeline_id not in pipelines:
        raise ValueError("Unable to find pipeline id '{i}'".format(i=args.pipeline_id))

    pipeline = pipelines[args.pipeline_id]

    if args.debug:
        slog.debug(args)

    ep_d = _cli_entry_point_args_to_dict(args.entry_points)

    return D.run_pipeline(pipelines, registered_files_d, registered_tasks_d, chunk_operators,
                          pipeline,
                          ep_d, args.output_dir, args.preset_xml, args.preset_rc_xml, args.mock)


def get_parser():
    p = get_base_parser()

    sp = p.add_subparsers(help='commands')

    def builder(subparser_id, description, options_func, exe_func):
        TU.subparser_builder(sp, subparser_id, description, options_func, exe_func)

    wf_desc = "Run a pipeline using a pipeline template or with explict Bindings and EntryPoints."
    builder('pipeline', wf_desc, add_pipline_parser_options, _args_run_pipeline)

    # Run a pipeline by id
    pipline_id_desc = "Run a registered pipline by specifiying the pipline id."
    builder('pipeline-id', pipline_id_desc, add_pipeline_id_parser_options, _args_run_pipeline_id)

    builder('task', "Run Task by id.", add_task_parser_options, _args_task_runner)

    # Show Templates
    desc = "List all pipeline templates. A pipeline 'id' can be referenced in your my_pipeline.xml file using '<import-template id=\"pbsmrtpipe.pipelines.my_pipeline_id\" />. This can replace the explicit listing of EntryPoints and Bindings."
    builder('show-templates', desc, lambda x: x, _args_run_show_templates)

    # Show Template Details
    builder('show-template-details', "Show details about a specific Pipeline template.", add_show_template_details_parser_options, _args_run_show_template_details)

    # Show Tasks
    builder('show-tasks', "Show completed list of Tasks by id", lambda x: x, _args_run_show_tasks)

    # Show Task id details
    desc_task_details = "Show Details of a particular task by id (e.g., 'pbsmrtpipe.tasks.filter_report'). Use 'show-tasks' to get a completed list of registered tasks."
    builder('show-task-details', desc_task_details, add_show_task_options, _args_run_show_task_details)

    wfo_desc = "Display all workflow level options that can be set in <options /> for preset.xml"
    builder('show-workflow-options', wfo_desc, _add_output_preset_xml_option, _args_run_show_workflow_level_options)

    return p


def _pbsmrtipe_setup_log(alog, **kwargs):
    """Setup stdout log. pbsmrtpipe will setup pbsmrtpipe.log, master.log

    This should only emit 'status.*' messages.
    """

    str_formatter = '[%(levelname)s] %(asctime)-15s %(message)s'

    setup_log(alog,
              level=logging.INFO,
              file_name=None,
              log_filter=StdOutStatusLogFilter(),
              str_formatter=str_formatter)

    slog.info("Starting pbsmrtpipe v{v}".format(v=pbsmrtpipe.get_version()))


def main(argv=None):

    argv_ = sys.argv if argv is None else argv
    parser = get_parser()

    return main_runner(argv_[1:], parser, args_executer, _pbsmrtipe_setup_log, log)