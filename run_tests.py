from argparse import ArgumentParser
import unittest

import xmlrunner

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.discover("./tests")

    parser = ArgumentParser(description="Run the Red Eye test suite")
    parser.add_argument(
        "-o", "--output", default="results.xml", help="File to output the results to"
    )
    args = parser.parse_args()

    with open(args.output, "wb") as output:
        runner = xmlrunner.XMLTestRunner(output=output)
        results = runner.run(suite)
        if len(results.failures) > 0:
            exit(1)
