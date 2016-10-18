# big-data-benchmark-suite-for-scala
Framework for easily create micro-benchmarks comparing Java and Scala performance

JaBMAny.java and ScBMAny.scala contain examples of how to create new microbenchmarks. Basically extend and implement the trait/interface Benchmark in your custom micro-benchmark.

No need to compile the source files, just run "./run.sh" and the python script will compile and run all source files and generate and xlxs report comparing different performance metrics.
