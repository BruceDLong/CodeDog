# CodeDog
Auto-generate programs in C derived languages for multiple platforms

This set of scripts compile CodeDog scripts into a C derived language. Modules are used to add new languages
and "patterns" can add new types of code it can generate.

The first module creates C++ code for Linux-based systems.

"Patterns" can be applied to generate code. For example, a parser/printer, a variable dumper, persistance,
or eventually things like GUIs. The program is structured such that programmer decisions like type of pointer to use,
choice of data-structure/algorithem or which libraries to use can be automated. Tags can be defined for different
builds to select priorities such as whether to prefer conserving memory or processor cycles or battery power.
Tags with patterns could also be used to select different data structures / algorithms in order to optimize 
according to a particular CPU's caching and lookahead features.
