import unittest
import specializer

class TestFunctionSpecializer(unittest.TestCase):
    def test_simple(self):
        def f(x):
            if x == 1:
                return 2
            return 3

        self.assertEquals(f(1), 2)
        self.assertEquals(f(2), 3)

        spec_f_1 = specializer.specialize_function(f, {'x': 1})

        self.assertEquals(spec_f_1(1), 2)
        self.assertEquals(spec_f_1(2), 2)

        spec_f_2 = specializer.specialize_function(f, {'x': 2})

        self.assertEquals(spec_f_2(1), 3)
        self.assertEquals(spec_f_2(2), 3)

    def test_else(self):
        def f(x):
            if x == 1:
                return 4
            else:
                return 5
            return 6

        self.assertEquals(f(1), 4)
        self.assertEquals(f(2), 5)

        spec_f_1 = specializer.specialize_function(f, {'x': 1})

        self.assertEquals(spec_f_1(1), 4)
        self.assertEquals(spec_f_1(2), 4)

        spec_f_2 = specializer.specialize_function(f, {'x': 2})

        self.assertEquals(spec_f_2(1), 5)
        self.assertEquals(spec_f_2(2), 5)

    def test_elif(self):
        def f(x):
            if x == 1:
                return 7
            elif x == 2:
                return 8
            else:
                return 9
            return 10

        self.assertEquals(f(1), 7)
        self.assertEquals(f(2), 8)
        self.assertEquals(f(3), 9)

        spec_f_1 = specializer.specialize_function(f, {'x': 1})

        self.assertEquals(spec_f_1(1), 7)
        self.assertEquals(spec_f_1(2), 7)
        self.assertEquals(spec_f_1(3), 7)

        spec_f_2 = specializer.specialize_function(f, {'x': 2})

        self.assertEquals(spec_f_2(1), 8)
        self.assertEquals(spec_f_2(2), 8)
        self.assertEquals(spec_f_2(3), 8)

        spec_f_3 = specializer.specialize_function(f, {'x': 3})

        self.assertEquals(spec_f_3(1), 9)
        self.assertEquals(spec_f_3(2), 9)
        self.assertEquals(spec_f_3(3), 9)

    def test_nested_if(self):
        def f(x):
            if x % 2 == 1:
                if x == 1:
                    return 11
                else:
                    return 12
            else:
                return 13
            return 14

        self.assertEquals(f(1), 11)
        self.assertEquals(f(2), 13)
        self.assertEquals(f(3), 12)

        spec_f_1 = specializer.specialize_function(f, {'x': 1})

        self.assertEquals(spec_f_1(1), 11)
        self.assertEquals(spec_f_1(2), 11)
        self.assertEquals(spec_f_1(3), 11)

        spec_f_2 = specializer.specialize_function(f, {'x': 2})

        self.assertEquals(spec_f_2(1), 13)
        self.assertEquals(spec_f_2(2), 13)
        self.assertEquals(spec_f_2(3), 13)

        spec_f_3 = specializer.specialize_function(f, {'x': 3})

        self.assertEquals(spec_f_3(1), 12)
        self.assertEquals(spec_f_3(2), 12)
        self.assertEquals(spec_f_3(3), 12)

    def test_nested_if_in_else(self):
        def f(x):
            if x == 4:
                return 15
            else:
                y = x + 2
                if x == 5:
                    return 16
            return 17

        self.assertEquals(f(4), 15)
        self.assertEquals(f(5), 16)
        self.assertEquals(f(6), 17)

        spec_f_5 = specializer.specialize_function(f, {'x': 5})
        self.assertEquals(spec_f_5(4), 16)
        self.assertEquals(spec_f_5(5), 16)
        self.assertEquals(spec_f_5(6), 16)

    def test_specialization_value_is_not_cached(self):
        def f(x):
            if x % 2 == 1:
                return x * 2
            else:
                return x + 1

        self.assertEquals(f(3), 6)
        self.assertEquals(f(4), 5)

        spec_f_odd = specializer.specialize_function(f, {'x': 1})
        self.assertEquals(spec_f_odd(3), 6)
        self.assertEquals(spec_f_odd(4), 8)

        spec_f_even = specializer.specialize_function(f, {'x': 2})
        self.assertEquals(spec_f_even(3), 4)
        self.assertEquals(spec_f_even(4), 5)

    def test_multiarg_and_nontrivial_condition(self):
        def f(xs, y):
            results = []
            for x in xs:
                if getattr(y, 'thingy'):
                    results.append(x*2)
                else:
                    results.append(x*3)
            return results

        class Thingy(object):
            def __init__(self, t):
                self.thingy = t

        t_true = Thingy(True)
        t_false = Thingy(False)

        self.assertEquals(f([1,2], t_true), [2,4])
        self.assertEquals(f([1,2], t_false), [3,6])

        spec_f_true = specializer.specialize_function(f, {'y': t_true})
        self.assertEquals(spec_f_true([1,2], t_true), [2,4])
        self.assertEquals(spec_f_true([1,2], t_false), [2,4])

        spec_f_false = specializer.specialize_function(f, {'y': t_false})
        self.assertEquals(spec_f_false([1,2], t_true), [3,6])
        self.assertEquals(spec_f_false([1,2], t_false), [3,6])

    def test_indeterminate_branching(self):
        def f(x, y):
            if x > y:
                r = x
            else:
                r = y
            return r

        self.assertEquals(f(1,5), 5)
        self.assertEquals(f(10,5), 10)

        spec_f_5 = specializer.specialize_function(f, {'y': 5})
        self.assertEquals(spec_f_5(1,5), 5)
        self.assertEquals(spec_f_5(10,5), 10)

    def test_indeterminate_and_determinate_branching(self):
        def f(x, y):
            if x > y:
                if y == 4:
                    return 128
                r = x
            else:
                r = y
            return r

        self.assertEquals(f(1,4), 4)
        self.assertEquals(f(10,4), 128)
        self.assertEquals(f(10,5), 10)

        spec_f_5 = specializer.specialize_function(f, {'y': 5})
        self.assertEquals(spec_f_5(1,4), 4)
        self.assertEquals(spec_f_5(10,4), 10)  # <= 5 != 5
        self.assertEquals(spec_f_5(10,5), 10)

        spec_f_4 = specializer.specialize_function(f, {'y': 4})
        self.assertEquals(spec_f_4(1,4), 4)
        self.assertEquals(spec_f_4(10,4), 128)
        self.assertEquals(spec_f_4(10,5), 128)  # !!


class TestInstanceMethodSpecializer(unittest.TestCase):
    def test_simple(self):
        class TestClass(object):
            def __init__(self):
                self.x = 'add'
                self.k = 2

            def do_things(self, y):
                if self.x == 'add':
                    return y + self.k
                elif self.x == 'multiply':
                    return y * self.k

        t = TestClass()
        self.assertEquals(t.do_things(3), 5)
        t.x = 'multiply'
        self.assertEquals(t.do_things(3), 6)
        t.k = 3
        self.assertEquals(t.do_things(3), 9)

        t = TestClass()
        t.do_things = specializer.specialize_instance_method(t, 'do_things')
        self.assertEquals(t.do_things(3), 5)
        t.x = 'multiply'
        self.assertEquals(t.do_things(3), 5)
        t.k = 4
        self.assertEquals(t.do_things(3), 7)






if __name__ == '__main__':
    unittest.main()

