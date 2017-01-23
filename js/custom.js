$(document).ready(function() {
  function round(float) {
    return Math.round(float * 100) / 100;
  }
  function get_machine_name(name) {
    return name.replace(/[ %*&()]+/g, '_');
  }
  function validate(min, max) {
    min = parseFloat(min);
    max = parseFloat(max);
    if (isNaN(min)) {
      return "Min must be a number";
    }
    if (isNaN(max)) {
      return "Max must be a number";
    }
    if (min > max) {
      return "Min must be less than max";
    }
    if (min < 0) {
      return "Min must be positive";
    }
    if (max < 0) {
      return "Max must be positive";
    }
    return "";
  }
  function createSlider(slider, name, machine_name, defaults) {
    var range = {'min': 0, 'max': defaults.max * 2} // range to choose from
    if (name.indexOf('%') !== -1) {
      range = {'min': 0, 'max': 100}
    }
    if (name == 'Energy kJ') {
      range = {'min': defaults.min * .9, 'max': defaults.max * 1.1}
    }
    noUiSlider.create(slider, {
      start: [defaults.min, defaults.max],
      connect: true,
      step: 1,
      behaviour: 'tap-drag',
      pips: {
        mode: 'count',
        values: 6,
        density: 4
      },
      range: range,
      format: {
        to: function(value) {
          return parseInt(value);
        },
        from: function(value) {
          return parseInt(value);
        }
      }
    });
    slider.noUiSlider.on('slide', function(values, handle) {
      // min handle = 0, max handle = 1
      if (handle) {
        $('#' + machine_name + ' input.max').val(values[handle]);
      } else {
        $('#' + machine_name + ' input.min').val(values[handle]);
      }
    });
    $('#' + machine_name + ' input.min').keyup(function() {
      slider.noUiSlider.set([$(this).val(), null]);
      var v = validate($(this).val(), $('#' + machine_name + ' input.max').val());
      this.setCustomValidity(v);
    });
    $('#' + machine_name + ' input.max').keyup(function() {
      slider.noUiSlider.set([null, $(this).val()]);
      var v = validate($('#' + machine_name + ' input.min').val(), $(this).val());
      this.setCustomValidity(v);
    });
  }
  $.get('get_nutrient_targets', function(data) {
    console.log(data);
    window.nutritional_targets = data;
    var keys = Object.keys(data).sort();
    for (var i in keys) {
      var person = keys[i];
      var selected = '';
      var fields = data[person];
      if (person == 'adult man') {
        selected = 'selected';
        var fields_sorted = Object.keys(fields).sort()
        $.each(fields_sorted, function(i, name) {
          var defaults = fields[name];
          var machine_name = get_machine_name(name)
          var display_name = name.charAt(0).toUpperCase() + name.slice(1);
          if (name == 'CHO % energy') {
            display_name = 'Carbohydrates % energy';
          }
          if (name == 'Free sugars % energy*') {
            display_name = 'Total sugars % energy';
          }
          $("#dynamic_fields").append('<div id="' + machine_name + '" class="row"><p class="nt_label">' + display_name + '</p><div class="input-field col s2"><input name="nt_' + name + '_min" value="' + round(defaults.min) + '" type="text" class="min validate"><label for="min">Min</label></div><div class="slider-wrapper col s8"><div class="slider"></div></div><div class="input-field col s2"><input type="text" name="nt_' + name + '_max" value="' + round(defaults.max) + '" class="max validate"><label for="max">Max</label></div></div>');
          var slider = $('#' + machine_name + ' div.slider')[0];
          createSlider(slider, name, machine_name, defaults)
        });
      }
      var person_display = person.replace('7 girl', '7-year-old girl').replace('adult women', 'adult woman').replace('14 boy', '14-year-old boy');
      if (!person_display.endsWith('C')) {
        person_display += ' H';
      }
      $('#person').append("<option " + selected + " value='" + person + "'>" + person_display + "</option>")
    }
    $('select').material_select();
    Materialize.updateTextFields();
    $('#person').change(function (e) {
      var p = $(this).val();
      var new_defaults = window.nutritional_targets[p];
      for (var name in new_defaults) {
        var defaults = new_defaults[name];
        if (!defaults) {
          console.error("No " + name + " nutritional constraint defined for " + p + "!");
          continue;
        }
        var machine_name = get_machine_name(name);
        $("#dynamic_fields #" + machine_name + " input.min").val(round(defaults.min));
        $("#dynamic_fields #" + machine_name + " input.max").val(round(defaults.max));
        $("#dynamic_fields #" + machine_name + " input.min").trigger('keyup');
        $("#dynamic_fields #" + machine_name + " input.max").trigger('keyup');
        var slider = $("#dynamic_fields #" + machine_name + " div.slider")[0];
        slider.noUiSlider.destroy();
        createSlider(slider, name, machine_name, defaults)
      }
      for (var name in window.foodGroupTargets) {
        if (!window.foodGroupTargets[name]['constraints_serves']) continue;
        var machine_name = get_machine_name(name);
        var defaults = window.foodGroupTargets[name]['constraints_serves'][p];
        if (!defaults) {
          console.error("No " + name + " food group serves constraint defined for " + p + "!");
          continue;
        }
        $("#dynamic_fields #" + machine_name + " input.min").val(round(defaults.min));
        $("#dynamic_fields #" + machine_name + " input.max").val(round(defaults.max));
        $("#dynamic_fields #" + machine_name + " input.min").trigger('keyup');
        $("#dynamic_fields #" + machine_name + " input.max").trigger('keyup');
        var slider = $("#dynamic_fields #" + machine_name + " div.slider")[0];
        slider.noUiSlider.destroy();
        createSlider(slider, name, machine_name, defaults)
      }
    });
    
    $.get('get_food_group_targets', function(data) {
      console.log(data);
      window.foodGroupTargets = data;
      var data_sorted = Object.keys(data).sort()
      $.each(data_sorted, function(i, name) {
        var constraints = data[name];
        if (!constraints['constraints_serves']) return;
        var machine_name = get_machine_name(name);
        var display_name = name.charAt(0).toUpperCase() + name.slice(1) + ' serves';
        var defaults = constraints['constraints_serves']['adult man'];
        if (!defaults) {
          console.error("No " + name + " defined for adult man!");
          return;
        }
        $("#dynamic_fields").append('<div id="' + machine_name + '" class="row"><p class="nt_label">' + display_name + '</p><div class="input-field col s2"><input name="fg_' + name + '_min" value="' + round(defaults.min) + '" type="text" class="min validate"><label for="min">Min</label></div><div class="slider-wrapper col s8"><div class="slider"></div></div><div class="input-field col s2"><input type="text" name="fg_' + name + '_max" value="' + round(defaults.max) + '" class="max validate"><label for="max">Max</label></div></div>');
        var slider = $('#' + machine_name + ' div.slider')[0];
        createSlider(slider, name, machine_name, defaults)
      });
      Materialize.updateTextFields();
    });
  });
  $.get('get_var_price', function(data) {
    var html = "";
    console.log(data);
    var icons = {
      "discount": "loyalty",
      "urban": "business",
      "season": "today",
      "deprivation": "trending_down",
      "population group": "perm_identity",
      "outlet type": "label",
      "type": "polymer",
      "region": "my_location"
    }
    var keys = Object.keys(data).sort()
    for (var i in keys) {
      var name = keys[i];
      var options = data[name];
      html += "<div class='input-field row'>";
      var icon = icons[name] || "stars";
      html += "<i class='material-icons prefix'>" + icon + "</i>";
      if (name == 'urban' || name == 'discount') {
        var checked = "", disabled = "";
        if (options.length == 1) {
          if (options[0] == 'urban' || options[0] == 'discount') {
            checked = 'checked ';
          }
          disabled = 'disabled ';
        }
        html += "<input id='vp_" + name + "' type='checkbox' " + checked + disabled + "</input><label for='vp_" + name + "'>" + name + "</label>";
      } else {
        var disabled = "";
        if (options.length == 1) {
          disabled = "disabled ";
        }
        html += "<select id='vp_" + name + "' " + disabled + ">";
        for (var j in options) {
          var text = options[j];
          html += "<option>" + text + "</option>";
        }
        html += "</select><label>" + name + "</label>";
      }
      html += "</div>";
    }
    html += "<div class='helpWrapper row'><i class='material-icons prefix'>live_help</i><span class='help card-panel'></span></div>";
    $("#var_price").append(html);
    $('select').material_select();
    $("#var_price input,select").change(function() {
      display_variable_prices();
    });
  });
  function display_variable_prices() {
    var runs = Object.keys(window.past_runs);
    if (!runs.length) return;
    var last_run = window.past_runs[runs[runs.length - 1]];
    if ($("#var_price_enabled").is(":checked")) {
      var scenario = {}
      $("#var_price :input").each(function(i, e) {
        if (e.id) {
          var v = $(e).val();
          if (e.id == 'vp_discount') {
            if ($(e).prop('checked')) {
              v = 'discount';
            } else {
              v = 'non-discount';
            }
          } else if (e.id == 'vp_urban') {
            if ($(e).prop('checked')) {
              v = 'urban';
            } else {
              v = 'rural';
            }
          }
          scenario[e.id] = v;
        }
      });
      var keys = Object.keys(scenario).sort();
      var vp_id = scenario[keys[0]];
      for (var i = 1; i < keys.length; i++) {
        var k = keys[i];
        vp_id += '_' + scenario[k];
      }
      console.log(vp_id);
      window.vp_id = vp_id;
      if (!last_run.stats.total_meal_plans) return;
      var vp = last_run.stats.variable_prices[vp_id];
      console.log(vp);
      if (vp) {
        $("#var_price .help").text("Combination effects price");
        $("#var_price .help").addClass('success');
        $("#summary #price").text(round(vp.mean));
        for (var h in last_run.meal_plans) {
          $("#" + h + " .totalPrice").text(round(last_run.meal_plans[h]['variable prices'][vp_id]));
          for (var g in last_run.meal_plans[h]['per_group']) {
            var machine_name = get_machine_name(g);
            try {
              var p = round(last_run.meal_plans[h]['per_group'][g]['variable prices'][vp_id]);
              if (p) {
                $("#" + h + " tr." + machine_name + " .price").text(p);
              }
            } catch(e) {
              console.error(h, g, vp_id, e);
            }
          }
        }
        calculate_combined_stats();
        return;
      } else {
        $("#var_price .help").text("No data for this combination");
        $("#var_price .help").removeClass('success');
      }
    }
    if (!last_run.stats.total_meal_plans) return;
    $("#summary #price").text(round(last_run.stats.price.mean));
    for (var h in last_run.meal_plans) {
      $("#" + h + " .totalPrice").text(round(last_run.meal_plans[h]['price']));
      for (var g in last_run.meal_plans[h]['per_group']) {
        var machine_name = get_machine_name(g);
        var p = round(last_run.meal_plans[h]['per_group'][g]['price']);
        $("#" + h + " tr." + machine_name + " .price").text(p);
      }
    }
    calculate_combined_stats();
  }
  $("#var_price_enabled").click(function() {
    $("#var_price").toggle();
    display_variable_prices();
  });
  window.past_runs = {};

  function calculate_combined_stats() {
    var selected = $.map($(".past_run.selected"), function(n) {
      return n.id;
    });
    combined_stats = {};
    // Sum up like persona stats
    for (var i in selected) {
      var ts = selected[i];
      var s = past_runs[ts].stats;
      var p = past_runs[ts].inputs.person;
      if (!s.total_meal_plans) continue;
      if (!combined_stats[p]) {
        combined_stats[p] = JSON.parse(JSON.stringify(s)); // Deep copy to prevent clobbering
        if (window.vp_id) {
          if (combined_stats[p].variable_prices[window.vp_id]) {
            combined_stats[p].variable_price = combined_stats[p].variable_prices[window.vp_id];
          }
          for (var g in s.per_group) {
            if (combined_stats[p].per_group[g].variable_prices && combined_stats[p].per_group[g].variable_prices[window.vp_id]) {
              combined_stats[p].per_group[g].variable_price = combined_stats[p].per_group[g].variable_prices[window.vp_id];
            }
          }
        }
        combined_stats[p].count = 1;
        continue;
      }
      combined_stats[p].count++;
      combined_stats[p]['total_meal_plans'] += s.total_meal_plans;
      for (var k in s) {
        if (k == 'price') {
          if (s[k]['min'] < combined_stats[p][k]['min']) {
            combined_stats[p][k]['min'] = s[k]['min'];
          }
          if (s[k]['max'] > combined_stats[p][k]['max']) {
            combined_stats[p][k]['max'] = s[k]['max'];
          }
          combined_stats[p][k]['mean'] += s[k]['mean'];
          combined_stats[p][k]['std'] += s[k]['std'];
        } else if (k == 'variable_prices' && combined_stats[p].variable_price) {
          if (s[k][window.vp_id].min < combined_stats[p].variable_price.min) {
            combined_stats[p].variable_price.min = s[k][window.vp_id].min;
          }
          if (s[k][window.vp_id].max > combined_stats[p].variable_price.max) {
            combined_stats[p].variable_price.max = s[k][window.vp_id].max;
          }
          combined_stats[p].variable_price.mean += s[k][window.vp_id].mean;
          combined_stats[p].variable_price.std += s[k][window.vp_id].std;
        } else if (k == 'variety') {
          if (s[k]['min'] < combined_stats[p][k]['min']) {
            combined_stats[p][k]['min'] = s[k]['min'];
          }
          if (s[k]['max'] > combined_stats[p][k]['max']) {
            combined_stats[p][k]['max'] = s[k]['max'];
          }
          combined_stats[p][k]['mean'] += s[k]['mean'];
        } else if (k == 'per_group' || k == 'variable_prices_by_var') {
          for (var g in s[k]) {
            for (var measure in s[k][g]) {
              if (measure == 'variable_prices') {
                if (window.vp_id && s[k][g][measure] && s[k][g][measure][window.vp_id]) {
                  if (s[k][g][measure][window.vp_id]['min'] < combined_stats[p][k][g][measure]['min']) {
                    combined_stats[p][k][g][measure]['min'] = s[k][g][measure][window.vp_id]['min'];
                  }
                  if (s[k][g][measure][window.vp_id]['max'] > combined_stats[p][k][g][measure]['max']) {
                    combined_stats[p][k][g][measure]['max'] = s[k][g][measure][window.vp_id]['max'];
                  }
                  combined_stats[p][k][g][measure]['mean'] += s[k][g][measure][window.vp_id]['mean'];
                }
              } else {
                if (!combined_stats[p][k][g][measure]) combined_stats[p][k][g][measure] = {'min':0, 'max':0, 'mean':0, 'std':0}
                if (s[k][g][measure]['min'] < combined_stats[p][k][g][measure]['min']) {
                  combined_stats[p][k][g][measure]['min'] = s[k][g][measure]['min'];
                }
                if (s[k][g][measure]['max'] > combined_stats[p][k][g][measure]['max']) {
                  combined_stats[p][k][g][measure]['max'] = s[k][g][measure]['max'];
                }
                combined_stats[p][k][g][measure]['mean'] += s[k][g][measure]['mean'];
                if (s[k][g][measure]['std']) {
                  combined_stats[p][k][g][measure]['std'] += s[k][g][measure]['std'];
                }
              }
            }
          }
        } else if (k == 'nutrition') {
          for (var n in s[k]) {
            if (s[k][n]['min'] < combined_stats[p][k][n]['min']) {
              combined_stats[p][k][n]['min'] = s[k][n]['min'];
            }
            if (s[k][n]['max'] > combined_stats[p][k][n]['max']) {
              combined_stats[p][k][n]['max'] = s[k][n]['max'];
            }
            combined_stats[p][k][n]['mean'] += s[k][n]['mean'];
          }
        }
      } 
    }
    
    var people = Object.keys(combined_stats);
    combined_stats.total_meal_plans = 1;
    combined_stats.count = 0;
    
    for (var i in people) {
      var p = people[i];
      var s = combined_stats[p];
      combined_stats.total_meal_plans *= s.total_meal_plans;
      combined_stats.count++;
      for (var k in s) {
        if (!combined_stats[k]) combined_stats[k] = {}
        if (k == 'price' || k == 'variable_price') {
          if (!combined_stats[k]['min']) combined_stats[k] = {'min':0,'max':0,'mean':0, 'std': 0}
          combined_stats[k]['min'] += s[k]['min'];
          combined_stats[k]['max'] += s[k]['max'];
          combined_stats[k]['mean'] += s[k]['mean'] / s.count;
          combined_stats[k]['std'] += s[k]['std'] / s.count;
        } else if (k == 'variety') {
          if (!combined_stats[k]['min']) combined_stats[k] = {'min':0,'max':0,'mean':0}
          combined_stats[k]['min'] += s[k]['min'];
          combined_stats[k]['max'] += s[k]['max'];
          combined_stats[k]['mean'] += s[k]['mean'] / s.count;
        } else if (k == 'per_group' || k == 'variable_prices_by_var') {
          for (var g in s[k]) {
            if (!combined_stats[k][g]) combined_stats[k][g] = {}
            for (var measure in s[k][g]) {
              if (!combined_stats[k][g][measure]) combined_stats[k][g][measure] = {'min':0, 'max': 0, 'mean': 0, 'std': 0}
              combined_stats[k][g][measure]['min'] += s[k][g][measure]['min'];
              combined_stats[k][g][measure]['max'] += s[k][g][measure]['max'];
              combined_stats[k][g][measure]['mean'] += s[k][g][measure]['mean'] / s.count;
              if (s[k][g][measure]['std']) {
                combined_stats[k][g][measure]['std'] += s[k][g][measure]['std'] / s.count;
              }
            }
          }
        } else if (k == 'nutrition') {
          for (var n in s[k]) {
            if (!combined_stats[k][n]) combined_stats[k][n] = {'min': 0, 'max': 0, 'mean': 0, 'std': 0}
            combined_stats[k][n]['min'] += s[k][n]['min'];
            combined_stats[k][n]['max'] += s[k][n]['max'];
            combined_stats[k][n]['mean'] += s[k][n]['mean'] / s.count;
          }
        }
      }
    }

    if (combined_stats.count == 0) {
      $('#past_runs_stats').empty();
      return;
    }
    
    combined_stats['variety']['min'] /= combined_stats.count;
    combined_stats['variety']['max'] /= combined_stats.count;
    combined_stats['variety']['mean'] /= combined_stats.count;
    
    for (var n in combined_stats['nutrition']) {
      combined_stats['nutrition'][n]['min'] /= combined_stats.count;
      combined_stats['nutrition'][n]['max'] /= combined_stats.count;
      combined_stats['nutrition'][n]['mean'] /= combined_stats.count;
    }

    if (combined_stats.variable_price) {
      var moe = 1.96 * combined_stats.variable_price.std / Math.sqrt(combined_stats.total_meal_plans);
      var lowerCI = combined_stats.variable_price.mean - moe;
      var upperCI = combined_stats.variable_price.mean + moe;
    } else {
      var moe = 1.96 * combined_stats.price.std / Math.sqrt(combined_stats.total_meal_plans);
      var lowerCI = combined_stats.price.mean - moe;
      var upperCI = combined_stats.price.mean + moe;
    }

    console.log(combined_stats);
    
    // Display

    var fgSum = "";
    var keys = Object.keys(combined_stats.per_group).sort();
    for (var i in keys) {
      var k = keys[i];
      var d = JSON.parse(JSON.stringify(combined_stats.per_group[k]));
      if (d['variable_price']) d['price'] = d['variable_price']
      fgSum += "<tr><td>" + k + "</td><td>" + round(d['amount']['min']) + "g-" + round(d['amount']['max']) + "g (" + round(d['amount']['mean']) + " avg)</td><td>$" + round(d['price']['min']) + "-$" + round(d['price']['max']) + " ($" + round(d['price']['mean']) + " avg)</td><td>" + round(d['serves']['min']) + "-" + round(d['serves']['max']) + " (" + round(d['serves']['mean']) + " avg)</td></tr>";
    }
    
    var nSum = "";
    var keys = Object.keys(combined_stats.nutrition).sort();
    for (var i in keys) {
      var k = keys[i];
      var d = combined_stats.nutrition[k];
      nSum += "<tr><td>" + k + "</td><td>" + round(d['min']) + "</td><td>" + round(d['mean']) + "</td><td>" + round(d['max']) + "</td></tr>";
    }
    
    var vpvSum = "";
    
    for (var k in combined_stats.variable_prices_by_var) {
      for (var v in combined_stats.variable_prices_by_var[k]) {
        var d = combined_stats.variable_prices_by_var[k][v];
        vpvSum += "<tr><td>" + k + ": " + v + "</td><td>$" + round(d['min']) + "</td><td>$" + round(d['mean']) + "</td><td>$" + round(d['max']) + "</td><td>" + round(d['std']) + "</td><tr>";
      }
    }
    
    var foodGroupTable = "<h4>Food group breakdown</h4><br><table class='highlight bordered'><thead><tr><th>Category</th><th>Amount</th><th>Price</th><th>Serves</th></tr></thead><tbody>" + fgSum + "</tbody></table>";
    var nutrientTable = "<h4>Average nutrition</h4><br><table class='highlight bordered'><thead><tr><th>Measure</th><th>Min</th><th>Average</th><th>Max</th></thead><tbody>" + nSum + "</tbody></table>";
    var vpvTable = "<h4>Variable price averages</h4><br><table class='highlight bordered'><thead><tr><th>Variable</th><th>Min</th><th>Mean</th><th>Max</th><th>σ</th></tr></thead><tbody>" + vpvSum + "</tbody></table>";
    
    var d = JSON.parse(JSON.stringify(combined_stats));
    if (d.variable_price) d.price = d.variable_price;
    var priceInfo = 'Price range: $' + round(d['price']['min']) + ' - $' + round(d['price']['max']) + ' ($' + round(d['price']['mean']) + ' avg). σ = ' + round(d.price.std) + ', 95% CI range = $' + round(lowerCI) + ' - $' + round(upperCI);
    var varietyInfo = 'Variety range: ' + round(combined_stats['variety']['min']) + '-' + round(combined_stats['variety']['max']) + ' (' + round(combined_stats['variety']['mean']) + ' avg)';
    var html = "Total combined meal plans: " + combined_stats['total_meal_plans'] + '<br>' + priceInfo + '<br>' + varietyInfo + '<br><br>' + foodGroupTable + "<br><br>" + nutrientTable + "<br><br>" + vpvTable;
    $('#past_runs_stats').html(html);
  }

  $("#past_runs_content").on('click', '.past_run', function() {
    $(this).toggleClass('selected');
    calculate_combined_stats();
  });
  function get_meal_plans(variables) {
    $('#progress').show();
    $.ajax({
      url: 'get_meal_plans',
      type: "POST",
      data: JSON.stringify(variables),
      dataType: "json",
      contentType: "application/json",
      success: function(data) {
        $('#progress').hide();
        console.log(data);
        window.past_runs[data.timestamp] = data;
        var details = data.inputs.person + '<br>Iteration limit: '  + data.inputs.iteration_limit + '<br>Minimum serve size difference: ' + data.inputs.min_serve_size_difference + '<br>' + data.stats.total_meal_plans + ' results';
        var card = '<div class="col s12 m6"><div class="card past_run" id="' + data.timestamp + '"><div class="card-content"><span class="card-title">' + data.timestamp + '</span><p>' + details + '</p></div></div></div>';
        $('#past_runs_content').append(card);
        $('#meal_plans').empty();
        for (var hash in data.meal_plans) {
          var o = data.meal_plans[hash];
          var items = "";
          var keys = Object.keys(o.meal).sort();
          for (var i in keys) {
            var k = keys[i];
            var amount = o.meal[k];
            items += "<tr><td>" + k + "</td><td>" + round(amount) + "g</td></tr>";
          }
          var fgSum = "";
          var keys = Object.keys(o.per_group).sort();
          for (var i in keys) {
            var k = keys[i];
            var d = o.per_group[k];
            fgSum += "<tr class='" + get_machine_name(k) + "'><td>" + k + "</td><td>" + round(d['amount']) + "g</td><td>$<span class='price'>" + round(d['price']) + "</span></td><td>" + round(d['serves']) + "</td></tr>";
          }
          var table = "<table class='highlight bordered'><thead><tr><th data-field='name'>Name</th><th data-field='amount'>Amount</th></tr></thead><tbody>" + items + "</tbody></table>";
          var collapsibleTable = "<ul class='collapsible' data-collapsible='accordion'><li><div class='collapsible-header'><i class='material-icons'>receipt</i>Items</div><div class='collapsible-body'>" + table + "</div></li></ul>";
          var foodGroupTable = "<h4>Food group breakdown</h4><br><table class='highlight bordered'><thead><tr><th>Category</th><th>Amount</th><th>Price</th><th>Serves</th></tr></thead>" + fgSum + "</table>";
          var summary = "<p class='priceWrapper'>Price: $<span class='totalPrice'>" + round(o.price) + "</span></p><p class='variety'>Variety: " + round(o.variety) + "</p>";
          var card = "<div id='" + hash + "' class='col s12 m6'><div class='card hoverable'><div class='card-content'>" + table + "</div><div class='card-action'>" + foodGroupTable + "<br>" + summary + "</div></div></div>";
          $('#meal_plans').append(card);
        }
        $('.collapsible').collapsible();
        var summary = "Total meal plans: " + data.stats.total_meal_plans + ". ";
        if (data.stats.total_meal_plans) {
          summary += "Average price: $<span id='price'>" + round(data.stats.price.mean) + "</span>. Average variety: " + round(data.stats.variety.mean) + ". ";
        }
        summary += "<a href='" + data.csv_file + "' class='waves-effect waves-light btn download-as-csv' download><i class='material-icons left'>play_for_work</i>Download as csv</a>";
        $('#summary').html(summary);
        display_variable_prices()
      }
    });
  }
  get_meal_plans({person: 'adult man'});
  $('#nutritional_constraints').submit(function( e ) {
    e.preventDefault();
    var variables = {'nutrient_targets': {}, 'food_group_targets': {}}
    $(this).serializeArray().map(function(x){
      if (x.name == 'variety') {
        if (!variables['variety']) variables['variety'] = [];
        variables['variety'].push(parseInt(x.value));
      } else if (x.name.startsWith('nt_')) {
        var bits = x.name.split('_')
        var measure = bits[1];
        var minormax = bits[2];
        if (!variables['nutrient_targets'][measure]) variables['nutrient_targets'][measure] = {}
        variables['nutrient_targets'][measure][minormax] = parseFloat(x.value);
      } else if (x.name.startsWith('fg_')) {
        var bits = x.name.split('_');
        var measure = bits[1];
        var minormax = bits[2];
        if (!variables['food_group_targets'][measure]) variables['food_group_targets'][measure] = {}
        variables['food_group_targets'][measure][minormax] = parseFloat(x.value);
      } else {
        variables[x.name] = x.value;
      }
    });
    console.log(variables);
    get_meal_plans(variables);
  });
  $('.modal-trigger').leanModal();
});