"""Rules for compiling Qt resource files."""

def _pyside6_rcc_impl(ctx):
    """Implementation for pyside6_rcc rule."""
    output = ctx.actions.declare_file(ctx.attr.out)
    
    args = ctx.actions.args()
    args.add("-o", output.path)
    args.add(ctx.file.src.path)
    
    ctx.actions.run(
        executable = ctx.executable._pyside6_rcc,
        arguments = [args],
        inputs = [ctx.file.src] + ctx.files.deps,
        outputs = [output],
        mnemonic = "PySide6Rcc",
        progress_message = "Compiling Qt resources %s" % ctx.file.src.short_path,
    )
    
    return [DefaultInfo(files = depset([output]))]

pyside6_rcc = rule(
    implementation = _pyside6_rcc_impl,
    attrs = {
        "src": attr.label(
            allow_single_file = [".qrc"],
            mandatory = True,
            doc = "The .qrc file to compile",
        ),
        "out": attr.string(
            mandatory = True,
            doc = "The output Python file name",
        ),
        "deps": attr.label_list(
            allow_files = True,
            doc = "Resource files referenced in the .qrc file",
        ),
        "_pyside6_rcc": attr.label(
            default = Label("@pip_deps//pyside6_essentials:pyside6_rcc"),
            executable = True,
            cfg = "exec",
        ),
    },
)
