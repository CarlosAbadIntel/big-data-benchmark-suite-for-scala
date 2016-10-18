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

import scala.runtime.ScalaRunTime

class ScBMArrayUpdate extends Benchmark {
  private var rnd_array: Array[Int] = _
  private var array: Array[Int] = _

  def warmUp(max_size: Int) {
    rnd_array = array_fill(max_size, 2939L)
    array = new Array[Int](max_size)

    for (i <- 0 until 2)
      run(max_size)
  }

  def run(size: Int) {
    for (i <- 0 until size)
      ScalaRunTime.array_update(array, rnd_array(i)%size, rnd_array(i))
  }

  private def array_fill(size: Int, rnd_seed: Long): Array[Int] = {
    var re_array: Array[Int] = new Array[Int](size)

    var rnd_gen: java.util.Random = new java.util.Random(rnd_seed)

    for (i <- 0 until size)
      re_array(i) = java.lang.Math.abs(rnd_gen.nextInt())

    return re_array
  }
}