import turtle as t
#=============hength of the block==============
a=50

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
t.pensize(15)
t.speed(0)
t.pencolor('black')
t.shape('arrow')
t.setheading(0)



#==========main programme==================


#画外框外围
fillcolor('skyblue')
up()
goto(-6,-7)
down()
beginfill()
goto(6,-7)
face(0)
c(1,90)
goto(7,6)
c(1,90)
goto(-6,7)
c(1,90)
goto(-7,-6)
c(1,90)
goto(6,-7)
endfill()

#画外框内部
fillcolor('white')
up()
goto(-5,-6)
down()
beginfill()
goto(5,-6)
c(1,90)
goto(6,5)
c(1,90)
goto(-5,6)
c(1,90)
goto(-6,-5)
c(1,90)
endfill()

#画M
up()
goto(0.5,0)
down()
fillcolor('royalblue')
beginfill()
goto(3.5,0)
c(-1,90)
goto(4.5,-4)
goto(3.5,-4)
goto(3.5,-1)
goto(2.5,-1)
goto(2.5,-4)
goto(1.5,-4)
goto(1.5,-1)
goto(0.5,-1)
goto(0.5,-4)
goto(-0.5,-4)
goto(-0.5,-1)
face(-90)
c(1,-90)
endfill()
up()


#画i

face(0)
goto(-1.5,-0.5)
fillcolor('red')
beginfill()
down()
goto(-1.5,-1.5)
goto(-2.5,-1.5)
goto(-2.5,-0.5)
goto(-1.5,-0.5)
endfill()
up()

goto(-1.5,-2)
down()
fillcolor('yellow')
beginfill()
goto(-1.5,-4)
goto(-2.5,-4)
goto(-2.5,-2)
goto(-1.5,-2)
endfill()
up()

#画P部分(外框)

goto(-3.5,-4)
down()
fillcolor('royalblue')
beginfill()
goto(-3.5,0)
goto(-1,0)
face(0)
c(0.5,90)
goto(-0.5,3)
c(1,90)
goto(-3.5,4)
c(1,90)
goto(-4.5,-4)
goto(-3.5,-4)
up()
endfill()

#画P的内部
goto(-1.5,1)
down()
fillcolor('white')
beginfill()
goto(-1.5,3)
goto(-3.5,3)
goto(-3.5,1)
goto(-1.5,1)
endfill()
up()

#画C
fillcolor('yellow')
beginfill()
goto(1,1)
down()
face(0)
goto(3,1)
c(0.5,90)
goto(3.5,2)
goto(1.5,2)
goto(1.5,3)
goto(3.5,3)
goto(3.5,3.5)
face(90)
c(0.5,90)
goto(1,4)
face(-180)
c(0.5,90)
goto(0.5,1.5)
face(-90)
c(0.5,90)
goto(3,1)
endfill()
up()
t.done()









