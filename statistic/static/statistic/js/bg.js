"use strict";
     var canvas = document.getElementById("canvas"),
      ctx = canvas.getContext("2d"),
      w = canvas.width = window.innerWidth, 
      h = canvas.height = window.innerHeight, 
      hue = 217, stars = [], count = 0, maxStars = 1300; 
      var canvas2 = document.createElement("canvas"), 
      ctx2 = canvas2.getContext("2d"); 
      canvas2.width = 100; 
      canvas2.height = 100; 
      var half = canvas2.width / 2, 
      gradient2 = ctx2.createRadialGradient(half, half, 0, half, half, half); 
      gradient2.addColorStop(0.025, "#CCC"); 
      gradient2.addColorStop(0.1, "hsl(" + hue + ", 61%, 33%)"); 
      gradient2.addColorStop(0.25, "hsl(" + hue + ", 64%, 6%)"); 
      gradient2.addColorStop(1, "transparent"); 
      ctx2.fillStyle = gradient2; ctx2.beginPath(); 
      ctx2.arc(half, half, half, 0, Math.PI * 2); 
      ctx2.fill(); 
      function random(c, b) { 
          if (arguments.length < 2) { 
              b = c; c = 0 
          } 
          if (c > b) { 
              var a = b; b = c; c = a 
         } 
         return Math.floor(Math.random() * (b - c + 1)) + c } 
        function maxOrbit(c, d) { 
            var b = Math.max(c, d), 
            a = Math.round(Math.sqrt(b * b + b * b)); 
            return a / 2 
        } 
        var Star = function () { 
            this.orbitRadius = random(maxOrbit(w, h)); 
            this.radius = random(60, this.orbitRadius) / 8; 
            this.orbitX = w / 2; 
            this.orbitY = h / 2; 
            this.timePassed = random(0, maxStars); 
            this.speed = random(this.orbitRadius) / 1000000; 
            this.alpha = random(2, 10) / 1000; 
            count++; 
            stars[count] = this 
        }; 
        Star.prototype.draw = function () { 
            var b = Math.sin(this.timePassed) * this.orbitRadius + this.orbitX, 
            c = Math.cos(this.timePassed) * this.orbitRadius + this.orbitY, a = random(10); 
            if (a === 1 && this.alpha > 0) { 
                this.alpha -= 0.05 
            } else { 
                if (a === 2 && this.alpha < 1) { 
                    this.alpha += 0.05 
                } 
            } 
            ctx.globalAlpha = this.alpha; 
            ctx.drawImage(canvas2, b - this.radius / 2, c - this.radius / 2, this.radius, this.radius); 
            this.timePassed += this.speed 
        }; 
        for (var i = 0; i < maxStars; i++) { 
            new Star() 
        } 
        function animation() { 
                ctx.globalCompositeOperation = "source-over"; 
                ctx.globalAlpha = 0.5; 
                ctx.fillStyle = "hsla(" + hue + ", 64%, 6%, 2)"; 
                ctx.fillRect(0, 0, w, h); 
                ctx.globalCompositeOperation = "lighter"; 
                for (var a = 1, b = stars.length; a < b; a++) { 
                    stars[a].draw() 
                } 
                window.requestAnimationFrame(animation) 
        } 
        animation();