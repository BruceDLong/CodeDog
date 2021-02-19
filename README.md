# CodeDog Programming language 2.0

NOTE: CodeDog is a work in progress. Most features work reliably on Linux. "xLators" and "library
converters" for Windows, MacOS, Android and iPhone are in various states of completion.
We're pedaling as fast as we can to make all of them complete and reliable!

While on the surface, CodeDog may look like every other “C++” like language, it is designed to be much more.
CodeDog programs specify complete apps that are to be built for a variety of platforms. To that end,
CodeDog automates many of the decisions that a developer would otherwise have to make. While easy to override,
decisions such as which data structure to use, which libraries to link, how a GUI should work or how to loop over a container are automated.

Some of the features are:
- Versions for multiple platforms can be built in one go.
- Creates native apps. CodeDog can compile to C++ to create Windows or Linux apps but can compile to Java or Swift for Android or Apple platforms.
- Chooses optimal data structures or algorithms based on Big-O and platform requirements. For example, it may use Arraylists in Java but deques in C++.
- Define whether it optimizes for speed, memory or power.
- Automatically generate a parser/extractor based on the fields in a class.
- "Patterns" are python scripts that can access your classes and modify them or add new ones. Patterns can automate tasks such as GUI generation.
- By analyzing the structure of types intended to be filled in by users, many user interfaces can be automatically generated. The generated apps can be styled. The default style conforms to the style expected by users of each target platform.
- In addition to GUI generation, a toolkit can generate the skeleton of a game app.
- For advanced users, define your own data structures and the criteria by which it would choose yours over a built in data structure. For example, your custom list may be better than Java’s ArrayList but in C++ a vector suits your programs needs better. Specify its pros can cons and let CodeDog choose.
- Automatically making choices based on aspects such as Big-O priorities, target platform and target language means that if an API is updated or deprecated, an update to CodeDog will fix it. Your apps will automatically update to better and more modern techniques just by rebuilding.
- Another philosophy of CodeDog is that the language should have a minimal but complete set of things to learn rather than a ton of features. If the features of a target language are optimal, CodeDog may implement your code using them, but you don’t have to learn about them or master them. You just do the simplest thing and let it make the choices.
- Since CodeDog can compile to optimized C++ or Swift (or later, Rust or GO, for example) it could be used to write AAA games or even an operating system. As people add more choices for it to use in implementing your code, eventually the code it produces will be highly secure, very optimized and based on Best Practices. It will even be able to generate special code optimized for your particular CPU and cache configuration.

We are working to have excellent documentation. Here is what we have so far: http://www.theslipstream.com/CodeDog/Docs/

Interested in trying CodeDog or contributing? Contact us:
  - Bruce: qstream@gmail.com
  - Tiffany: ktiffanyWalker@gmail.com
