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
