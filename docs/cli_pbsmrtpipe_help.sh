usage: pbsmrtpipe [-h] [-v]
                  {pipeline,pipeline-id,task,show-templates,show-template-details,show-tasks,show-task-details,show-workflow-options}
                  ...

Pbsmrtpipe workflow engine

positional arguments:
  {pipeline,pipeline-id,task,show-templates,show-template-details,show-tasks,show-task-details,show-workflow-options}
                        commands
    pipeline            Run a pipeline using a pipeline template or with
                        explict Bindings and EntryPoints.
    pipeline-id         Run a registered pipline by specifiying the pipline
                        id.
    task                Run Task by id.
    show-templates      List all pipeline templates. A pipeline 'id' can be
                        referenced in your my_pipeline.xml file using
                        '<import-template
                        id="pbsmrtpipe.pipelines.my_pipeline_id" />. This can
                        replace the explicit listing of EntryPoints and
                        Bindings.
    show-template-details
                        Show details about a specific Pipeline template.
    show-tasks          Show completed list of Tasks by id. Use ENV
                        PB_TOOL_CONTRACT_DIR to define a custom directory of
                        tool contracts. These TCs will override the installed
                        TCs (e.g., PB_TOOL_CONTRACT_DIR=/path/to/my-tc-dir/)
    show-task-details   Show Details of a particular task by id (e.g.,
                        'pbsmrtpipe.tasks.filter_report'). Use 'show-tasks' to
                        get a completed list of registered tasks.
    show-workflow-options
                        Display all workflow level options that can be set in
                        <options /> for preset.xml

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit
