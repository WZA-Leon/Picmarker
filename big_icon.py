import turtle as t
#=============hength of the block==============
a=30

#=============define fast entrances=======================
def up():
    t.up()

def down():
    t.pendown()

def goto(x,y):
    t.goto(x*a,y*a)  
    
def c(r,angle):
    t.circle(r*a,angle)
    
def l():
    t.left()
    
def r():
    t.right()    
    
def face(angle):				
    t.setheading(angle) 

def fillcolor(color):
    t.fillcolor(color)
def beginfill():
    t.begin_fill()
    
def endfill():
    t.end_fill()
    
    
    
    
#==========init=============================
t.pensize(10)
t.speed(0)
t.pencolor('black')
t.shape('arrow')
t.setheading(0)



#==========main programme==================

#a外框
down()
fillcolor('royalblue')
beginfill()
goto(0,0)
goto(2.5,0)
goto(2.5,1)
goto(2,1)
goto(2,2)
face(90)
c(1,90)
goto(0,3)
c(1,90)
goto(-1,1)
c(1,90)
endfill()
up()
#a 内侧
goto(0,1)
down()
fillcolor('white')
beginfill()
goto(1,1)
goto(1,2)
goto(0,2)
goto(0,1)
endfill()
up()

#r
goto(3.5,0)
down()
fillcolor('skyblue')
beginfill()
goto(4.5,0)
goto(4.5,1.5)
face(90)
c(-0.5,90)
goto(5,2)
goto(5,3)
goto(4.5,3)
face(180)
c(1,90)
goto(3.5,0)
endfill()
up()

#k
goto(6,0)
down()
fillcolor('royalblue')
beginfill()
goto(7,0)
goto(7,1)
goto(7.5,1)
goto(8,0)
goto(9,0)
goto(8.125,1.5)
goto(9,3)
goto(8,3)
goto(7.5,2)
goto(7,2)
goto(7,5)
goto(6,5)
goto(6,0)
endfill()
up()

#e
goto(10,0)
down()
goto(13,0)
goto(13,1)
beginfill()
goto(13,3)
goto(10,3)
goto(10,0)
goto(13,0)
goto(13,1)
endfill()
up()
goto(12,2)
down()
goto(11,2)
goto(11,1)
goto(13,1)
up()

#r
fillcolor('skyblue')
goto(14,0)
down()
beginfill()
goto(15,0)
goto(15,1.5)
face(90)
c(-0.5,90)
goto(16,2)
goto(16,3)
goto(15,3)
face(180)
c(1,90)
goto(14,0)
endfill()
up()

#m
goto(-2,0)
down()
fillcolor('royalblue')
beginfill()
goto(-2,2)
face(90)
c(1,90)
goto(-6,3)
c(1,90)
goto(-7,0)
goto(-6,0)
goto(-6,2)
goto(-5,2)
goto(-5,0)
goto(-4,0)
goto(-4,2)
goto(-3,2)
goto(-3,0)
goto(-2,0)
endfill()
up()

#c
goto(-9,0)
down()
fillcolor('yellow')
beginfill()
face(0)
c(1,90)
goto(-10,1)
goto(-10,2)
goto(-8,2)
face(90)
c(1,90)
goto(-10,3)
c(1,90)
goto(-11,1)
c(1,90)
goto(-9,0)
endfill()
up()

#i
goto(-13,0)
down()
fillcolor('yellow')
beginfill()
goto(-12,0)
goto(-12,2)
goto(-13,2)
goto(-13,0)
endfill()
up()

goto(-13,3)
down()
fillcolor('red')
beginfill()
goto(-12,3)
goto(-12,4)
goto(-13,4)
goto(-13,3)
endfill()
up()

#P
goto(-15,0)
down()
fillcolor('royalblue')
beginfill()
goto(-14,0)
goto(-14,3)
goto(-13,3)
goto(-13,4)
goto(-14,4)
goto(-14,6)
goto(-12,6)
goto(-12,3)
face(0)
c(1,90)
goto(-11,6)
c(1,90)
goto(-14,7)
c(1,90)
goto(-15,0)
endfill()

t.done()









