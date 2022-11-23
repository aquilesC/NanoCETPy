# Contributing

Contributions to **NanoCETPy** are always welcome, and they are greatly appreciated! 

If you have a question about the use of the software, or want to learn more, the proper place is the [discussion forum](https://github.com/Dispertech/NanoCETPy/discussions). Our developers and other contributors are always paying attention to the upcoming questions to offer the best support. 

If you have found a bug in the software, you can report it by [creating an issue](https://github.com/Dispertech/NanoCETPy/issues). The more description you give in the form of screenshots, information on what was the status of the system when the bug appeared, etc. will help speed up the troubleshooting process. 

**Ideas for improvement** can also be submited as a [feature request](https://github.com/Dispertech/NanoCETPy/issues) or can be suggested in [the discussion forum](https://github.com/Dispertech/NanoCETPy/discussions).  

## Code contributions
Before contributing code, it is wise to reach out through the forum, or [by e-mail](https://dispertech.com/contact/) to be sure there is not more than one person working on the same features or bug problems. 

All contributions should be sent to the official [Github repository](https://github.com/Dispertech/NanoCETPy) in the form of a **merge request**. Please do not submit git diffs or files containing the changes.

`NanoCETPy` is an open-source python package under the license of [GNUv3](https://github.com/Dispertech/NanoCETPy/blob/main/LICENSE.md). 
We consider the act of contributing to the code by submitting a Merge Request as the "Sign off" or agreement to the GNUv3 license.

You can contribute in many different ways:

## Other Types of Contributions

### Report Bugs

Report bugs at [Github Issues](https://github.com/Dispertech/NanoCETPy/issues).

### Fix Issues
Look through the Github issues. Different tags are indicating the status of the issues.
The "bug" tag indicates problems with NanoCETPy, while the "enhancement" tag shows ideas that should be added in the future. 

Before starting to work on the code, make sure you let others know by asking to be assigned to that issue. 

### Write Documentation

The documentation of NanoCETPy can be found [here](http://nanocetpy.readthedocs.io/). 

If you found a better way to explain how to use the code, the program, the GUI, you can contribute to [the documentation](https://github.com/Dispertech/NanoCETPy/tree/main/docs).  

## Get Started!

Ready to contribute? Here is how to set up `NanoCETPy` for local development.

1. Fork the `NanoCETPy` repo on GitHub.
2. Clone your fork locally:
```bash
    $ git clone https://github.com/USERNAME/NanoCETPy.git
    $ cd NanoCETPy
```
3. Install your local copy into a virtualenv.
```bash
    $ pip install virtualenvwrapper-win (windows)/ pip install virtualenvwrapper (linux)
    $ mkvirtualenv NanoCETPy
    $ pip install -e .
```

By following the comments, you can also install all dependencies with the specific versions that we tested for Python 3.9.7:
```bash
    $ pip install -r requirements.txt
```

4. Create a branch for local development:
```bash
    $ git checkout -b name-of-your-bugfix-or-feature
```
   Now you can make your changes locally.

   To get all packages needed for development, a requirements list can be found [here](https://github.com/Dispertech/NanoCETPy/blob/main/setup.py).

5. Commit your changes and push your branch to GitHub::
```bash
    $ git add .
    $ git commit -m "Your detailed description of your changes."
    $ git push origin name-of-your-bugfix-or-feature
```
6. Submit a Merge Request on Github.

## Merge Request Guidelines

Before you submit a Merge Request, check that it meets these guidelines:

- If the Merge Request adds functionality, the docs should be updated. Put your new functionality into a function with a docstring.
- If you have a maintainer status for `NanoCETPy`, you can merge Merge Requests to the main branch. However, every Merge Request needs to be reviewed by another developer. Thus it is not allowed to merge a Merge Request, which is submitted by oneself.

