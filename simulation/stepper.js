/*
 * simulation/stepper.js — ตัวควบคุมทีละขั้น
 * ถือรายการ steps ที่ core บันทึกไว้แล้ว เลื่อน index ไปมาได้ (ถัดไป / ย้อนกลับ / เล่นซ้ำ)
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.BankerStepper = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  class Stepper {
    constructor(steps) {
      this.steps = steps || [];
      this.index = 0;
    }
    get current() {
      return this.steps[this.index];
    }
    get atStart() {
      return this.index === 0;
    }
    get atEnd() {
      return this.index >= this.steps.length - 1;
    }
    next() {
      if (!this.atEnd) this.index++;
      return this.current;
    }
    prev() {
      if (!this.atStart) this.index--;
      return this.current;
    }
    reset() {
      this.index = 0;
      return this.current;
    }
    end() {
      this.index = Math.max(0, this.steps.length - 1);
      return this.current;
    }
  }
  return { Stepper };
});
