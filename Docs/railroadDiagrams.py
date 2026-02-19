#!/usr/bin/env python3
# See https://tabatkins.github.io/railroad-diagrams/generator.html

from railroad import *

buildDir = "./build/html"

def writeDiagram(filename, diagram):
    fullName = buildDir +"/" + filename+".svg"
    f = open(fullName, "w")
    diagram.writeSvg(f.write)
    f.close()

    with open(fullName) as f:
        lines = f.read().splitlines()

    titleStr = '<text style="text-anchor:start" font-family="Verdana" font-size="64" fill="darkgray" x="15" y="15">DIAGRAM_NAME</text>'
    titleStr = titleStr.replace("DIAGRAM_NAME", filename)
    lines.insert(1, titleStr)
    lines[2]='<g transform="translate(.5 10.5)">'

    f = open(fullName, "w")
    for line in lines:
        f.write(line+"\n")
    f.close()

# CodeDog Program
writeDiagram("CodeDog_Program", Diagram(
   ZeroOrMore(NonTerminal('BuildSpec')),
   ZeroOrMore(NonTerminal('TagDefinition')),
   ZeroOrMore(NonTerminal('ClassDefinition'))
))

# tag definition
writeDiagram("TagDefinition", Diagram(
  NonTerminal('identifier'), '=',
  Choice(2,
     NonTerminal('quotedString'),
     NonTerminal('multilineString'),
     NonTerminal('tagKeyword'),
     NonTerminal('tagList'),
     NonTerminal('tagMap'),
     Sequence('<', NonTerminal('fieldSpec'), '>')
  )
))

# tag list
# tag map

# Build Spec
writeDiagram("buildSpec", Diagram(
   NonTerminal('buildIdentifier'), ':',ZeroOrMore(NonTerminal('TagDefinition')), ';'
))

# Class Definition
writeDiagram("ClassDefinition", Diagram(
   Choice(1, 'model', 'struct', 'string'), NonTerminal('className'),
   Optional(Sequence(':', OneOrMore(NonTerminal('Tag Definition')))),
   NonTerminal('Structure Spec')
))

# Structure Spec
writeDiagram("StructureSpec", Diagram(
   Choice( 0,
      Group(Sequence('{', ZeroOrMore(NonTerminal('FieldDef')), '}'), 'Field Sequence'),
      Group(Sequence('[', OneOrMore(
                    Choice(0,NonTerminal('FieldDef'), NonTerminal('CoFactual')),
                '|'), ']'), 'Field Alternates')
   )
))

# coFactual

# Field Def
writeDiagram("FieldDef", Diagram(
   Choice(2, "const", "my", "me", "our", "their", "we", "itr"),
   Choice(1, NonTerminal('classID'), NonTerminal('baseType'), NonTerminal('numberRange'), NonTerminal('modeSpec'), 'flag'),
   Optional(NonTerminal('NameAndValue'))
))

# NameAndValue
writeDiagram("NameAndValue", Diagram(
   Sequence(
       Choice(0,':','::'), NonTerminal('fieldName'),
       Choice(0,
                 Group(Sequence('<-', NonTerminal('Expression')), 'assignment'),
                 Group(Sequence('{', OneOrMore(NonTerminal('Initialization')), '}'), 'static initialization'),
                 Group( Sequence('(', NonTerminal('argList'), ')',
                        Optional(Sequence(':', ZeroOrMore(NonTerminal('tagDef')))),
                        '<-', NonTerminal('FunctionBody')), "functionDef"),
          )
       )
   )
)

# -------------------------
# withEach (single diagram)
# -------------------------
writeDiagram("withEach", Diagram(
  Sequence(
    'withEach',

    Group(Sequence(
        Choice(0,
            # tuple binding: (k, v)
            Group(Sequence('(', NonTerminal('identifier'), ',', NonTerminal('identifier'), ')'), '(key, value) binding'),
            # single binding: [axis] name
            Group(Sequence(Optional(NonTerminal('loopBindMode')), NonTerminal('identifier')), 'single binding'),
        )
    ), "Binding"),

    Group(Sequence(
        Choice(0,
            # numeric range source: in range: A..B / A..=B
            Group(Sequence('in', 'range', ':', NonTerminal('rangeSpec')), 'numeric range source'),

            # traversal source: in <container> [mode] [rangeClause]
            Group(Sequence(
                'in',
                NonTerminal('Expression'),                    # container
                Optional(NonTerminal('traversalMode')),       # Forward/Backward/etc
                Optional(NonTerminal('rangeClause')),         # keys:/index:/iters: + rangeSpec
            ), "container traversal source"),

            # file source: FILE(expr)
            Group(Sequence('FILE', '(', NonTerminal('Expression'), ')'), 'file source'),
        )
    ), "Source"),

    Group(Sequence(
        Optional(Sequence('skip', NonTerminal('Expression'))),
        Optional(Sequence('take', NonTerminal('Expression'))),
        Optional(Sequence('where', '(', NonTerminal('Expression'), ')')),
        Optional(Sequence('until', '(', NonTerminal('Expression'), ')')),
    ), "Modifiers"),

    Group(NonTerminal('actionSeq'), "Body"),
  )
))

# Optional: keep these if you want them referenced as NonTerminal(...) items above
writeDiagram("loopBindMode", Diagram(
    Choice(0, 'key', 'value', 'entry', 'index', 'iter')
))

writeDiagram("traversalMode", Diagram(
    Choice(0, 'Forward', 'Backward', 'Preorder', 'Inorder', 'Postorder', 'BreadthFirst', 'DF_Iterative')
))

writeDiagram("rangeClause", Diagram(
    Sequence(
        Choice(0, 'keys', 'index', 'iters'),
        ':',
        NonTerminal('rangeSpec')
    )
))

writeDiagram("rangeSpec", Diagram(
    Sequence(
        Optional(NonTerminal('Expression')),
        Choice(0, '..', '..='),
        Optional(NonTerminal('Expression')),
    )
))

