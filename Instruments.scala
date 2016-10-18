/*
Copyright (c) 2016, Intel Corporation

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice,
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Intel Corporation nor the names of its contributors
      may be used to endorse or promote products derived from this software
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
*/

import java.io._

trait Benchmark {
  def warmUp(max_size: Int): Unit
  def run(size:Int): Unit
}

object Instruments {
  def main(args: Array[String]) {
    // Benchmark parameters
    var class_name: String = args(0)
    var min_size: Int = args(1).toInt               // 1K
    var max_size: Int = args(2).toInt               // 1B
    var run_time: Long = args(3).toLong*1000000000L // 300000000000L ns
    var tag: String = args(4)

    // Performance data storage
    var array_size: Int = java.lang.Math.log10(max_size/min_size).toInt + 1
    var avg_time_log = new Array[Long](array_size)
    var size_log = new Array[Int](array_size)
    var iterations_log = new Array[Long](array_size)

    // Instantiating benchmark
    var bm: Benchmark = Class.forName(class_name).newInstance().asInstanceOf[Benchmark]

    // benchmark/JVM warmup
    println("starting warmup")
    bm.warmUp(max_size)
    println("Warmup finished")

    // run benchmark for <run_time> seconds
    var size:Int = min_size
    var start_time: Long = System.nanoTime()
    var iterations: Long = 0L
    var total_time: Long = 0L

    activateJFR()
    startJFR()

    while (size <= max_size) {
      var time: Long = System.nanoTime()

      bm.run(size)
  
      var time2: Long = System.nanoTime()
      total_time += (time2 - time)
      iterations += 1L

      if ((time2 - start_time) >= run_time) {
        stopJFR("%s_%s_%d.jfr".format(class_name, tag, size))

        var avg_time: Long = total_time/(iterations*1000L)

        println(s"Size $size finished in ${avg_time} us, averaged over $iterations runs")

        var pos: Int = java.lang.Math.log10(size/min_size).toInt
        avg_time_log(pos) = avg_time
        size_log(pos) = size
        iterations_log(pos) = iterations

        size *= 10
        start_time = System.nanoTime()
        iterations = 0L
        total_time = 0L

        if (size <= max_size) {
          Thread.sleep(1000)
          startJFR()
        }
      }
    }

    printToCSV(class_name, tag, args(3), size_log, avg_time_log, iterations_log)
  }

  // Java Flight recorder
  def activateJFR() = {
    println("Activating Java Commercial Features")
    var cmd = "jcmd MainGenericRunner VM.unlock_commercial_features"
    var p: Process = Runtime.getRuntime().exec(cmd)
    readProcessOutput(p)
  }

  def startJFR() = {
    println("Starting Java Flight Recorder")
    var cmd = "jcmd MainGenericRunner JFR.start name=bm settings=modified_profile.jfc"
    var p: Process = Runtime.getRuntime().exec(cmd)
    readProcessOutput(p)
  }

  def stopJFR(jfr_filename: String) = {
    println("Java Flight Recorder Done")

    var cmd = "jcmd MainGenericRunner JFR.dump name=bm filename=" + jfr_filename
    var p: Process = Runtime.getRuntime().exec(cmd);
    readProcessOutput(p)

    cmd = "jcmd MainGenericRunner JFR.stop name=bm"
    p = Runtime.getRuntime().exec(cmd);
    readProcessOutput(p)
  }

  def readProcessOutput(p: Process) = {
    var stdInput: BufferedReader  = new BufferedReader(new InputStreamReader(p.getInputStream()));
    var stdError: BufferedReader = new BufferedReader(new InputStreamReader(p.getErrorStream()));

    readBufferOutput(stdInput)
    readBufferOutput(stdError)
  }

  def readBufferOutput(buffer: BufferedReader) = {
    var s: String = null;
    var cont: Boolean = true

    while(cont) {
      s = buffer.readLine()

      if(s == null)
        cont = false    
      else
        println(s)
    }
  }

  // Printing to a CSV file
  def printToCSV(name: String, tag: String, run_time: String, size_log: Array[Int], avg_time_log: Array[Long], iterations_log:Array[Long]) = {
    val B2MBL: Long = 1024L * 1024L   // Bytes to MBs
    val B2KBL: Long = 1024L           // Bytes to KBs
    val U2NSL: Long = 1000L           // ns to us

    var file: File = new File(name + ".csv")

    var bw: BufferedWriter = null

    if(!file.exists()) {
      file.createNewFile()
      bw = new BufferedWriter(new FileWriter(file.getAbsoluteFile(), false))
    } else {
      bw = new BufferedWriter(new FileWriter(file.getAbsoluteFile(), true))
    }

    // Print out the header
    bw.write(tag)
    bw.newLine()

    bw.write(s"Size, log(size), Runs in $run_time secs, Operations in $run_time secs, Time/run (us), Time/operation (us)")
    bw.newLine()

    for (i <- 0 until size_log.length) {
      var str = "%d, %d, %d, %d, %d, %d"
      bw.write(str.format(size_log(i), 
                          java.lang.Math.log10(size_log(i)).toInt,
                          iterations_log(i),
                          size_log(i)*iterations_log(i),
                          avg_time_log(i),
                          avg_time_log(i)/size_log(i)))
      bw.newLine()
    }

    bw.close()
  }
}