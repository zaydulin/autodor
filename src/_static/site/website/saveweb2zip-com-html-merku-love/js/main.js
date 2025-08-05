// ==================================================
// * Project Name   :  ProMotors – Car Service & Detailing Template
// * File           :  JS Base
// * Version        :  1.0.0
// * Last change    :  06 July 2023, Thursday
// * Author         :  Merkulove (https://1.envato.market/tf-merkulove)
// ==================================================

(function($) {
  "use strict";

  // Vanilla Calendar - Start
  // --------------------------------------------------
  document.addEventListener('DOMContentLoaded', () => {
    const calendar = new VanillaCalendar('.vanilla-calendar');
    calendar.init();
  });
  // Vanilla Calendar - End
  // --------------------------------------------------

  // Back To Top - Start
  // --------------------------------------------------
  $(window).scroll(function() {
    if ($(this).scrollTop() > 200) {
      $('.backtotop:hidden').stop(true, true).fadeIn();
    } else {
      $('.backtotop').stop(true, true).fadeOut();
    }
  });
  $(function() {
    $(".scroll").on('click', function() {
      $("html,body").animate({scrollTop: 0}, "slow");
      return false
    });
  });
  // Back To Top - End
  // --------------------------------------------------

  // sticky header - Start
  // --------------------------------------------------
  $(window).on('scroll', function () {
    if ($(this).scrollTop() > 0) {
      $('.site_header').addClass("sticky")
    } else {
      $('.site_header').removeClass("sticky")
    }
  });
  // sticky header - End
  // --------------------------------------------------

  // Splitting Text Animation - Start
  // --------------------------------------------------
  $(window).on("load", function () {
    Splitting({
      target: "[data-splitting]",
      by: "chars"
    });
  });
  // Splitting Text Animation - End
  // --------------------------------------------------

  // wow js - Start
  // --------------------------------------------------
  var wow = new WOW({
    animateClass: 'animated',
    offset: 100,
    mobile: true,
    duration: 400,
  });
  wow.init();
  // wow js - End
  // --------------------------------------------------

  // Tilt - Start
  // --------------------------------------------------
  $('.tilt').tilt({
    maxTilt:        12,
    perspective:    1000,
    scale:          1,
    speed:          1000,
    glare:          false,
    maxGlare:       1
  });
  // Tilt - End
  // --------------------------------------------------

  // Dropdown - Start
  // --------------------------------------------------
  $(document).ready(function () {
    $(".dropdown").on('mouseover', function () {
      $(this).find('> .dropdown-menu').addClass('show');
    });
    $(".dropdown").on('mouseout', function () {
      $(this).find('> .dropdown-menu').removeClass('show');
    });
  });
  // Dropdown - End
  // --------------------------------------------------

  // Odometer Counter - Start
  // --------------------------------------------------
  jQuery('.odometer').appear(function (e) {
    var odo = jQuery(".odometer");
    odo.each(function () {
      var countNumber = jQuery(this).attr("data-count");
      jQuery(this).html(countNumber);
    });
  });
  // Odometer Counter - End
  // --------------------------------------------------

  // Background Parallax - Start
  // --------------------------------------------------
  $('.parallaxie').parallaxie({
    speed: 0.5,
    offset: 0,
  });
  // Background Parallax - End
  // --------------------------------------------------

  // Videos & Images popup - Start
  // --------------------------------------------------
  $('.popup_video').magnificPopup({
    type: 'iframe',
    preloader: false,
    removalDelay: 160,
    mainClass: 'mfp-fade',
    fixedContentPos: false
  });

  $('.zoom-gallery').magnificPopup({
    delegate: '.popup_image',
    type: 'image',
    closeOnContentClick: false,
    closeBtnInside: false,
    mainClass: 'mfp-with-zoom mfp-img-mobile',
    gallery: {
      enabled: true
    },
    zoom: {
      enabled: true,
      duration: 300,
      opener: function(element) {
        return element.find('img');
      }
    }

  });
  // Videos & Images popup - End
  // --------------------------------------------------

  // Multy Countdown - Start
  // --------------------------------------------------
  $('.countdown_timer').each(function(){
    $('[data-countdown]').each(function() {
      var $this = $(this), finalDate = $(this).data('countdown');
      $this.countdown(finalDate, function(event) {
        var $this = $(this).html(event.strftime(''
          + '<li class="days_count"><strong>%D</strong><span>Days</span></li>'
          + '<li class="hours_count"><strong>%H</strong><span>Hours</span></li>'
          + '<li class="minutes_count"><strong>%M</strong><span>Mins</span></li>'
          + '<li class="seconds_count"><strong>%S</strong><span>Secs</span></li>'));
      });
    });
  });
  // Multy Countdown - End
  // --------------------------------------------------

  // main slider - start
  // --------------------------------------------------
  $('.main_slider').slick({
    dots: true,
    fade: true,
    speed: 1000,
    arrows: true,
    infinite: true,
    autoplay: true,
    slidesToShow: 1,
    autoplaySpeed: 6000,
    prevArrow: ".main_left_arrow",
    nextArrow: ".main_right_arrow",
    asNavFor: '.main_slider_nav'
  });
  $('.main_slider_nav').slick({
    dots: false,
    arrows: false,
    infinite: true,
    // vertical: true,
    slidesToShow: 4,
    slidesToScroll: 1,
    focusOnSelect: true,
    // verticalSwiping: true,
    asNavFor: '.main_slider',
    responsive: [
    {
      breakpoint: 576,
      settings: {
        slidesToShow: 1,
      }
    },
    {
      breakpoint: 992,
      settings: {
        slidesToShow: 2,
      }
    },
    {
      breakpoint: 1025,
      settings: {
        slidesToShow: 4,
      }
    }
    ]
  });

  $('.main_slider').on('init', function (e, slick) {
    var $firstAnimatingElements = $('div.slider_item:first-child').find('[data-animation]');
    doAnimations($firstAnimatingElements);
  });
  $('.main_slider').on('beforeChange', function (e, slick, currentSlide, nextSlide) {
    var $animatingElements = $('div.slider_item[data-slick-index="' + nextSlide + '"]').find('[data-animation]');
    doAnimations($animatingElements);
  });
  var slideCount = null;

  $('.main_slider').on('init', function (event, slick) {
    slideCount = slick.slideCount;
    setSlideCount();
    setCurrentSlideNumber(slick.currentSlide);
  });
  $('.main_slider').on('beforeChange', function (event, slick, currentSlide, nextSlide) {
    setCurrentSlideNumber(nextSlide);
  });

  function setSlideCount() {
    var $el = $('.slide_count_wrap').find('.total');
    if (slideCount < 10) {
      $el.text('0' + slideCount);
    } else {
      $el.text(slideCount);
    }
  }

  function setCurrentSlideNumber(currentSlide) {
    var $el = $('.slide_count_wrap').find('.current');
    $el.text(currentSlide + 1);
  }

  function doAnimations(elements) {
    var animationEndEvents = 'webkitAnimationEnd mozAnimationEnd MSAnimationEnd oanimationend animationend';
    elements.each(function () {
      var $this = $(this);
      var $animationDelay = $this.data('delay');
      var $animationType = 'animated ' + $this.data('animation');
      $this.css({
        'animation-delay': $animationDelay,
        '-webkit-animation-delay': $animationDelay
      });
      $this.addClass($animationType).one(animationEndEvents, function () {
        $this.removeClass($animationType);
      });
    });
  }

  var $timer = 6000;
  function progressBar() {
    $(".slick-progress").find("span").removeAttr("style");
    $(".slick-progress").find("span").removeClass("active");
    setTimeout(function () {
      $(".slick-progress").find("span").css("transition-duration", $timer / 1000 + "s").addClass("active");
    }, 100);
  }

  progressBar();
  $('.main_slider').on("beforeChange", function (e, slick) {
    progressBar();
  });
  // main slider - end
  // --------------------------------------------------

  // Carousels - Start
  // --------------------------------------------------
  $('.carousel_1col').slick({
    dots: true,
    speed: 1000,
    arrows: true,
    infinite: true,
    autoplay: true,
    slidesToShow: 1,
    pauseOnHover: true,
    autoplaySpeed: 5000,
    prevArrow: ".c1c_arrow_left",
    nextArrow: ".c1c_arrow_right"
  });

  $('.carousel_2col').slick({
    dots: true,
    speed: 1000,
    arrows: true,
    infinite: true,
    autoplay: true,
    slidesToShow: 2,
    slidesToScroll: 2,
    pauseOnHover: true,
    autoplaySpeed: 5000,
    prevArrow: ".c2c_arrow_left",
    nextArrow: ".c2c_arrow_right",
    responsive: [
    {
      breakpoint: 992,
      settings: {
        slidesToShow: 1,
        slidesToScroll: 1
      }
    }
    ]
  });

  $('.carousel_3col').slick({
    dots: true,
    speed: 1000,
    arrows: true,
    infinite: true,
    autoplay: true,
    slidesToShow: 3,
    slidesToScroll: 3,
    pauseOnHover: true,
    autoplaySpeed: 5000,
    prevArrow: ".c3c_arrow_left",
    nextArrow: ".c3c_arrow_right",
    responsive: [
    {
      breakpoint: 576,
      settings: {
        slidesToShow: 1,
        slidesToScroll: 1
      }
    },
    {
      breakpoint: 992,
      settings: {
        slidesToShow: 2,
        slidesToScroll: 2
      }
    }
    ]
  });

  $('.carousel_4col').slick({
    dots: true,
    speed: 1000,
    arrows: true,
    infinite: true,
    autoplay: true,
    slidesToShow: 4,
    slidesToScroll: 4,
    pauseOnHover: true,
    autoplaySpeed: 5000,
    prevArrow: ".c4c_arrow_left",
    nextArrow: ".c4c_arrow_right",
    responsive: [
    {
      breakpoint: 576,
      settings: {
        slidesToShow: 1,
        slidesToScroll: 1
      }
    },
    {
      breakpoint: 992,
      settings: {
        slidesToShow: 2,
        slidesToScroll: 2
      }
    },
    {
      breakpoint: 1025,
      settings: {
        slidesToShow: 3,
        slidesToScroll: 3
      }
    }
    ]
  });

  $('.carousel_5col').slick({
    dots: true,
    speed: 1000,
    arrows: true,
    infinite: true,
    autoplay: true,
    slidesToShow: 5,
    slidesToScroll: 1,
    pauseOnHover: true,
    autoplaySpeed: 5000,
    prevArrow: ".c5c_arrow_left",
    nextArrow: ".c5c_arrow_right",
    responsive: [
    {
      breakpoint: 576,
      settings: {
        slidesToShow: 1,
        centerPadding: '40px',
        centerMode: true
      }
    },
    {
      breakpoint: 992,
      settings: {
        slidesToShow: 2
      }
    },
    {
      breakpoint: 1025,
      settings: {
        slidesToShow: 3
      }
    },
    {
      breakpoint: 1200,
      settings: {
        slidesToShow: 4
      }
    }
    ]
  });

  $('.carousel_6col').slick({
    dots: true,
    speed: 1000,
    arrows: true,
    infinite: true,
    autoplay: true,
    slidesToShow: 6,
    slidesToScroll: 1,
    pauseOnHover: true,
    autoplaySpeed: 5000,
    prevArrow: ".c6c_arrow_left",
    nextArrow: ".c6c_arrow_right",
    responsive: [
    {
      breakpoint: 576,
      settings: {
        slidesToShow: 1,
        centerPadding: '40px',
        centerMode: true
      }
    },
    {
      breakpoint: 991,
      settings: {
        slidesToShow: 2
      }
    },
    {
      breakpoint: 1025,
      settings: {
        slidesToShow: 3
      }
    },
    {
      breakpoint: 1200,
      settings: {
        slidesToShow: 4
      }
    },
    {
      breakpoint: 1461,
      settings: {
        slidesToShow: 5
      }
    }
    ]
  });
  // Carousels - End
  // --------------------------------------------------

  // Carousels - Start
  // --------------------------------------------------
  $('.brand_logo_carousel').slick({
    dots: false,
    speed: 8000,
    arrows: false,
    autoplay: true,
    infinite: true,
    slidesToShow: 5,
    autoplaySpeed: 0,
    centerMode: true,
    cssEase: 'linear',
    pauseOnHover: true,
    responsive: [
    {
      breakpoint: 576,
      settings: {
        speed: 800,
        autoplay: false,
        slidesToShow: 1
      }
    },
    {
      breakpoint: 768,
      settings: {
        speed: 800,
        autoplay: false,
        slidesToShow: 2
      }
    },
    {
      breakpoint: 1025,
      settings: {
        slidesToShow: 3
      }
    },
    {
      breakpoint: 1200,
      settings: {
        slidesToShow: 4
      }
    }
    ]
  });
  // Carousels - End
  // --------------------------------------------------

  // Details Image Carousel - Start
  // --------------------------------------------------
  $('.details_image_carousel').slick({
    dots: false,
    arrows: false,
    slidesToShow: 1,
    slidesToScroll: 1,
    asNavFor: '.details_image_carousel_nav'
  });
  $('.details_image_carousel_nav').slick({
    dots: false,
    arrows: false,
    vertical: true,
    slidesToShow: 4,
    slidesToScroll: 1,
    focusOnSelect: true,
    verticalSwiping: true,
    asNavFor: '.details_image_carousel'
  });
  // Details Image Carousel - End
  // --------------------------------------------------

  // Brand Logo Blur Effect - Start
  // --------------------------------------------------
  $('.brand_logo_blur_effect .brand_logo_item').hover(function () {
    $('.brand_logo_blur_effect .brand_logo_item').css({
      opacity: '.4',
      filter: 'blur(2px)',
      transition: 'all .4s'
    })
    $(this).css({
      opacity: '1',
      filter: 'blur(0)',
      transition: 'all .4s'
    })
  }, function () {
    $('.brand_logo_blur_effect .brand_logo_item').css({
      opacity: '1',
      filter: 'blur(0)',
      transition: 'all .4s'
    })
  });
  // Brand Logo Blur Effect - End
  // --------------------------------------------------

  // Image Before After - Start
  // --------------------------------------------------
  $(".image_before_after").beforeAfter({
    movable: true,
    clickMove: true,
    alwaysShow: true,
    position: 50,
    opacity: 0.8,
    hoverOpacity: 1,
    activeOpacity: 1,
    separatorColor: "#D16527",
    bulletColor: "#D16527",
    arrowColor: "#FFFFFF",
  });
  // Image Before After - End
  // --------------------------------------------------

  // Priceing Range - Start
  // --------------------------------------------------
  if($("#slider-range").length){
    $("#slider-range").slider({
      range: true,
      min: 0,
      max: 1000,
      values: [5.0, 355.0],
      slide: function (event, ui) {
        $("#amount").val("$" + ui.values[0] + " - $" + ui.values[1]);
      },
    });
    $( "#amount" ).val( "$" + $( "#slider-range" ).slider( "values", 0 ) +
      " - $" + $( "#slider-range" ).slider( "values", 1 ) );
  }

  $('.ar_top').on('click', function () {
    var getID = $(this).next().attr('id');
    var result = document.getElementById(getID);
    var qty = result.value;
    $('.proceed_to_checkout .update-cart').removeAttr('disabled');
    if( !isNaN( qty ) ) {
      result.value++;
    }else{
      return false;
    }
  });
  // Priceing Range - End
  // --------------------------------------------------

  // Quantity Form - start
  // --------------------------------------------------
  (function() {
    window.inputNumber = function(el) {
      var min = el.attr("min") || false;
      var max = el.attr("max") || false;
      var els = {};
      els.dec = el.prev();
      els.inc = el.next();
      el.each(function() {
        init($(this));
      });
      function init(el) {
        els.dec.on("click", decrement);
        els.inc.on("click", increment);

        function decrement() {
          var value = el[0].value;
          value--;
          if (!min || value >= min) {
            el[0].value = value;
          }
        }
        function increment() {
          var value = el[0].value;
          value++;
          if (!max || value <= max) {
            el[0].value = value++;
          }
        }
      }
    };
  })();
  inputNumber($(".input_number"));
  // Quantity Form - end
  // --------------------------------------------------

})(jQuery);
